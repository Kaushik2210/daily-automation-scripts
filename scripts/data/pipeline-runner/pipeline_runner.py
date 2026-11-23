"""Run a chain of data steps (read, filter, join, group, sort, write...) from a YAML file."""
import argparse
import ast
import csv
import json
import operator
import re
import sys
from pathlib import Path

import yaml

ARITHMETIC = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.Div: operator.truediv, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv}
AGGREGATES = {"count", "sum", "mean", "min", "max"}


class StepError(Exception):
    pass


def number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def show(value):
    """Format a computed number: whole numbers without .0, others to 6 decimals."""
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else f"{round(value, 6):g}"
    return str(value)


def compare(cell, op, wanted):
    left, right = number(cell), number(wanted)
    if op in ("==", "!=", ">", ">=", "<", "<=") and left is not None and right is not None:
        cell, wanted = left, right
    else:
        cell, wanted = str(cell), str(wanted)
    table = {"==": operator.eq, "!=": operator.ne, ">": operator.gt, ">=": operator.ge,
             "<": operator.lt, "<=": operator.le}
    if op in table:
        return table[op](cell, wanted)
    if op == "contains":
        return wanted.lower() in cell.lower()
    if op == "startswith":
        return cell.lower().startswith(wanted.lower())
    if op == "endswith":
        return cell.lower().endswith(wanted.lower())
    if op == "matches":
        return re.search(wanted, cell) is not None
    raise StepError(f"unknown filter operator '{op}'")


def evaluate(expression, row):
    """Safe arithmetic on a row's columns: only numbers, column names and + - * / % //."""
    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            value = number(row.get(node.id))
            if node.id not in row:
                raise StepError(f"no column '{node.id}' in the expression")
            if value is None:
                raise ValueError("empty")
            return value
        if isinstance(node, ast.BinOp) and type(node.op) in ARITHMETIC:
            return ARITHMETIC[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return -walk(node.operand) if isinstance(node.op, ast.USub) else walk(node.operand)
        raise StepError("expressions may only use numbers, column names and + - * / % //")
    try:
        return show(walk(ast.parse(expression, mode="eval")))
    except (ValueError, ZeroDivisionError):
        return ""  # an empty or invalid input gives an empty result
    except SyntaxError:
        raise StepError(f"can't read the expression '{expression}'") from None


def read_csv(path, delimiter=","):
    try:
        with Path(path).open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            columns = [c.strip() for c in next(reader, [])]
            rows = [dict(zip(columns, r + [""] * (len(columns) - len(r)), strict=False))
                    for r in reader if r]
    except OSError as err:
        raise StepError(f"can't read {path}: {err.strerror or err}") from None
    return columns, rows


def need(spec, key, step):
    if not isinstance(spec, dict) or key not in spec:
        raise StepError(f"'{step}' needs '{key}'")
    return spec[key]


def check_columns(columns, wanted, step):
    missing = [c for c in wanted if c not in columns]
    if missing:
        raise StepError(f"'{step}': no such column {', '.join(missing)} (have: "
                        f"{', '.join(columns)})")


def sort_key(value):
    parsed = number(value)
    return (0, parsed, "") if parsed is not None else (1, 0.0, str(value).lower())


def aggregate(values, func):
    numbers = [n for n in (number(v) for v in values) if n is not None]
    if func == "count":
        return str(len([v for v in values if str(v).strip()]))
    if not numbers:
        return ""
    return show({"sum": sum(numbers), "mean": sum(numbers) / len(numbers), "min": min(numbers),
                 "max": max(numbers)}[func])


def run_step(kind, spec, columns, rows, apply, written):
    """Apply one step. Returns (columns, rows)."""
    if kind == "read":
        path = spec if isinstance(spec, str) else need(spec, "file", kind)
        delimiter = spec.get("delimiter", ",") if isinstance(spec, dict) else ","
        return read_csv(path, delimiter)
    if not columns and kind != "write":
        raise StepError(f"'{kind}' needs data: start the pipeline with a 'read' step")
    if kind == "filter":
        column, op = need(spec, "column", kind), spec.get("op", "==")
        check_columns(columns, [column], kind)
        if op in ("is_empty", "not_empty"):
            keep = [r for r in rows if bool(r[column].strip()) == (op == "not_empty")]
        else:
            keep = [r for r in rows if compare(r[column], op, need(spec, "value", kind))]
        return columns, keep
    if kind in ("select", "drop"):
        wanted = [spec] if isinstance(spec, str) else list(spec)
        check_columns(columns, wanted, kind)
        kept = [c for c in columns if c not in wanted] if kind == "drop" else wanted
        return kept, [{c: r[c] for c in kept} for r in rows]
    if kind == "rename":
        check_columns(columns, list(spec), kind)
        names = [spec.get(c, c) for c in columns]
        return names, [{spec.get(c, c): r[c] for c in columns} for r in rows]
    if kind == "sort":
        by = need(spec, "by", kind)
        by = [by] if isinstance(by, str) else list(by)
        check_columns(columns, by, kind)
        ordered = sorted(rows, key=lambda r: [sort_key(r[c]) for c in by],
                         reverse=bool(spec.get("desc")))
        return columns, ordered
    if kind == "dedupe":
        subset = columns if spec in (True, None) else ([spec] if isinstance(spec, str) else spec)
        check_columns(columns, subset, kind)
        seen, unique = set(), []
        for row in rows:
            key = tuple(row[c] for c in subset)
            if key not in seen:
                seen.add(key)
                unique.append(row)
        return columns, unique
    if kind == "limit":
        if not isinstance(spec, int) or spec < 0:
            raise StepError("'limit' needs a whole number")
        return columns, rows[:spec]
    if kind == "fill":
        column = need(spec, "column", kind)
        check_columns(columns, [column], kind)
        value = str(need(spec, "value", kind))
        return columns, [{**r, column: r[column] if r[column].strip() else value} for r in rows]
    if kind == "add_column":
        name = need(spec, "name", kind)
        if "expr" in spec:
            made = [evaluate(spec["expr"], r) for r in rows]
        elif "template" in spec:
            try:
                made = [spec["template"].format(**r) for r in rows]
            except KeyError as err:
                raise StepError(f"'add_column': no such column {err}") from None
        else:
            made = [str(need(spec, "value", kind))] * len(rows)
        out_columns = columns if name in columns else [*columns, name]
        return out_columns, [{**r, name: v} for r, v in zip(rows, made, strict=True)]
    if kind == "group":
        by = need(spec, "by", kind)
        by = [by] if isinstance(by, str) else list(by)
        check_columns(columns, by, kind)
        plan = spec.get("agg", {})
        for column, func in plan.items():
            check_columns(columns, [column], kind)
            if func not in AGGREGATES:
                choices = ", ".join(sorted(AGGREGATES))
                raise StepError(f"'group': unknown function '{func}' (use {choices})")
        groups = {}
        for row in rows:
            groups.setdefault(tuple(row[c] for c in by), []).append(row)
        out_columns = [*by, *(f"{c}_{f}" for c, f in plan.items()), "count"]
        result = []
        for key, members in groups.items():
            item = dict(zip(by, key, strict=True))
            for column, func in plan.items():
                item[f"{column}_{func}"] = aggregate([m[column] for m in members], func)
            item["count"] = str(len(members))
            result.append(item)
        return out_columns, result
    if kind == "join":
        file, on = need(spec, "file", kind), need(spec, "on", kind)
        right_on = spec.get("right_on", on)
        extra_columns, extra_rows = read_csv(file)
        check_columns(columns, [on], kind)
        check_columns(extra_columns, [right_on], kind)
        lookup = {}
        for row in extra_rows:
            lookup.setdefault(row[right_on], row)
        added = [c for c in extra_columns if c != right_on and c not in columns]
        inner = spec.get("how", "left") == "inner"
        joined = []
        for row in rows:
            match = lookup.get(row[on])
            if match is None and inner:
                continue
            joined.append({**row, **{c: (match or {}).get(c, "") for c in added}})
        return [*columns, *added], joined
    if kind == "write":
        path = Path(spec if isinstance(spec, str) else need(spec, "file", kind))
        written.append((path, len(rows)))
        if apply:
            if path.exists():
                raise StepError(f"{path} already exists; choose another name")
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle, lineterminator="\n")
                writer.writerow(columns)
                writer.writerows([r.get(c, "") for c in columns] for r in rows)
        return columns, rows
    raise StepError(f"unknown step '{kind}'")


def describe(kind, spec):
    text = json.dumps(spec, ensure_ascii=False) if not isinstance(spec, str) else spec
    return f"{kind} {text}"[:70]


def run(pipeline, apply):
    """Run all steps. Returns (log lines, final columns, final rows, files written)."""
    steps = pipeline.get("steps") if isinstance(pipeline, dict) else None
    if not isinstance(steps, list) or not steps:
        raise StepError("the pipeline needs a 'steps' list")
    columns, rows, log, written = [], [], [], []
    for number_, step in enumerate(steps, 1):
        if not isinstance(step, dict) or len(step) != 1:
            raise StepError(f"step {number_} must be a single 'name: settings' entry")
        (kind, spec), = step.items()
        try:
            columns, rows = run_step(kind, spec, columns, rows, apply, written)
        except StepError as err:
            raise StepError(f"step {number_} ({kind}): {err}") from None
        log.append(f"{number_:>2}. {describe(kind, spec):<70} -> {len(rows)} row(s), "
                   f"{len(columns)} column(s)")
    return log, columns, rows, written


def preview(columns, rows, limit=5):
    shown = [[r.get(c, "") for c in columns] for r in rows[:limit]]
    widths = [max([len(c)] + [len(r[i]) for r in shown]) for i, c in enumerate(columns)]
    lines = ["  " + " | ".join(c.ljust(w) for c, w in zip(columns, widths, strict=True)),
             "  " + "-+-".join("-" * w for w in widths)]
    lines += ["  " + " | ".join(v.ljust(w) for v, w in zip(r, widths, strict=True)) for r in shown]
    return "\n".join(line.rstrip() for line in lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a data pipeline from a YAML file.")
    parser.add_argument("pipeline", type=Path, help="pipeline file (YAML or JSON)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the output files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.pipeline.is_file():
        parser.error(f"not a file: {args.pipeline}")
    try:
        text = args.pipeline.read_text(encoding="utf-8")
        pipeline = json.loads(text) if args.pipeline.suffix == ".json" else yaml.safe_load(text)
    except (OSError, ValueError, yaml.YAMLError) as err:
        print(f"Can't read the pipeline: {err}", file=sys.stderr)
        return 1
    try:
        log, columns, rows, written = run(pipeline, args.apply)
    except StepError as err:
        print(f"Pipeline stopped: {err}", file=sys.stderr)
        return 1
    print(f"Pipeline: {pipeline.get('name', args.pipeline.stem)}\n")
    print("\n".join(log))
    if rows:
        print(f"\nResult (first {min(5, len(rows))} of {len(rows)} row(s)):\n"
              + preview(columns, rows))
    for path, count in written:
        print(f"\n{'Wrote' if args.apply else 'Would write'} {path} ({count} row(s))"
              + ("" if args.apply else ". Use --apply to do it."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
