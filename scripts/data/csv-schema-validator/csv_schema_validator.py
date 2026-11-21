"""Validate a CSV file against a schema of column types and rules, or infer a schema from it."""
import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

TRUE_FALSE = {"true", "false", "yes", "no", "y", "n", "1", "0", "t", "f"}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_value(text, kind, fmt=None):
    """Convert text to the column type; raise ValueError when it doesn't fit."""
    if kind == "int":
        return int(text)
    if kind == "float":
        return float(text)
    if kind == "bool":
        if text.lower() not in TRUE_FALSE:
            raise ValueError("not a true/false value")
        return text.lower() in ("true", "yes", "y", "1", "t")
    if kind == "date":
        return datetime.strptime(text, fmt or "%Y-%m-%d").date()
    if kind == "datetime":
        return datetime.strptime(text, fmt or "%Y-%m-%d %H:%M:%S")
    return text


def check_cell(text, spec):
    """Return a problem description for one non-empty cell, or None."""
    kind = spec.get("type", "str")
    try:
        value = parse_value(text, kind, spec.get("format"))
    except ValueError:
        hint = f" (expected format {spec['format']})" if spec.get("format") else ""
        return f"is not a valid {kind}{hint}"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "min" in spec and value < spec["min"]:
            return f"is below the minimum of {spec['min']}"
        if "max" in spec and value > spec["max"]:
            return f"is above the maximum of {spec['max']}"
    if kind == "str":
        if "min_length" in spec and len(text) < spec["min_length"]:
            return f"is shorter than {spec['min_length']} characters"
        if "max_length" in spec and len(text) > spec["max_length"]:
            return f"is longer than {spec['max_length']} characters"
    if "allowed" in spec and text not in [str(a) for a in spec["allowed"]]:
        return f"is not one of {', '.join(map(str, spec['allowed']))}"
    if "pattern" in spec and not re.search(spec["pattern"], text):
        return f"does not match the pattern {spec['pattern']}"
    return None


def validate(rows, header, schema):
    """Return (list of (line, column, value, problem), set of structural problems)."""
    columns = schema.get("columns", {})
    structure = []
    missing = [c for c in columns if c not in header]
    structure += [f"missing column '{c}'" for c in missing]
    if schema.get("strict"):
        structure += [f"unexpected column '{c}'" for c in header if c not in columns]
    if len(set(header)) != len(header):
        structure.append("duplicate column names in the header")
    errors, seen = [], {c: {} for c, s in columns.items() if s.get("unique")}
    for line, row in rows:
        if len(row) != len(header):
            errors.append((line, "(row)", "", f"has {len(row)} fields, expected {len(header)}"))
            continue
        record = dict(zip(header, row, strict=True))
        for name, spec in columns.items():
            if name not in record:
                continue
            value = record[name].strip()
            if value == "":
                if spec.get("required"):
                    errors.append((line, name, "", "is required but empty"))
                continue
            problem = check_cell(value, spec)
            if problem:
                errors.append((line, name, value, problem))
            if name in seen:
                if value in seen[name]:
                    errors.append((line, name, value, f"is a duplicate (first seen on line "
                                                      f"{seen[name][value]})"))
                else:
                    seen[name][value] = line
    return errors, structure


def infer_column(values):
    """Guess a column spec from its non-empty values."""
    spec = {"type": "str"}
    if values:
        if all(re.fullmatch(r"-?\d+", v) for v in values):
            spec = {"type": "int", "min": min(int(v) for v in values),
                    "max": max(int(v) for v in values)}
        elif all(_is_float(v) for v in values):
            spec = {"type": "float", "min": min(float(v) for v in values),
                    "max": max(float(v) for v in values)}
        elif all(v.lower() in TRUE_FALSE and not v.isdigit() for v in values):
            spec = {"type": "bool"}
        elif all(ISO_DATE.match(v) and _valid_date(v) for v in values):
            spec = {"type": "date", "format": "%Y-%m-%d"}
        elif len(set(values)) <= 6 and len(values) >= 2 * len(set(values)):
            spec = {"type": "str", "allowed": sorted(set(values))}
    return spec


def _is_float(text):
    try:
        float(text)
    except ValueError:
        return False
    return True


def _valid_date(text):
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        return [h.strip() for h in header], [(reader.line_num, row) for row in reader if row]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a CSV file against a schema.")
    parser.add_argument("csv", type=Path)
    parser.add_argument("schema", type=Path, nargs="?", help="schema file (JSON)")
    parser.add_argument("--infer", action="store_true",
                        help="print a schema guessed from the CSV instead of validating")
    parser.add_argument("--max-errors", type=int, default=20, help="problems to list (20)")
    args = parser.parse_args(argv)
    if not args.csv.is_file():
        parser.error(f"not a file: {args.csv}")
    header, rows = read_csv(args.csv)
    if not header:
        print("The CSV file is empty.", file=sys.stderr)
        return 1

    if args.infer:
        columns = {}
        for index, name in enumerate(header):
            values = [row[index].strip() for _, row in rows if index < len(row)
                      and row[index].strip()]
            spec = infer_column(values)
            if len(values) == len(rows):
                spec["required"] = True
            if len(rows) > 1 and len(set(values)) == len(values) == len(rows) and spec[
                    "type"] in ("int", "str"):
                spec["unique"] = True
            columns[name] = spec
        print(json.dumps({"strict": True, "columns": columns}, indent=1))
        return 0
    if not args.schema:
        parser.error("give a schema file, or use --infer to create one")
    try:
        schema = json.loads(args.schema.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        print(f"Can't read the schema: {err}", file=sys.stderr)
        return 1

    errors, structure = validate(rows, header, schema)
    for message in structure:
        print(f"STRUCTURE  {message}")
    for line, column, value, problem in errors[:args.max_errors]:
        shown = f" '{value}'" if value else ""
        print(f"line {line:<4} {column:<12}{shown} {problem}")
    if len(errors) > args.max_errors:
        print(f"... and {len(errors) - args.max_errors} more")
    by_column = {}
    for _, column, _, _ in errors:
        by_column[column] = by_column.get(column, 0) + 1
    summary = ", ".join(f"{c} ({n})" for c, n in sorted(by_column.items(), key=lambda i: -i[1]))
    bad_lines = len({e[0] for e in errors})
    print(f"\n{len(rows)} row(s) checked: {len(errors)} problem(s) on {bad_lines} row(s)"
          + (f" - {summary}" if summary else "") + f", {len(structure)} structure problem(s).")
    return 1 if errors or structure else 0


if __name__ == "__main__":
    sys.exit(main())
