"""Monthly expense summary from a CSV: category breakdown, comparison, budgets and top items."""
import argparse
import calendar
import csv
import json
import sys
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

CENT = Decimal("0.01")


def read_expenses(path):
    """Return (rows, problems); a row is {date, amount, category, note}."""
    rows, problems = [], []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        names = {(n or "").strip().lower() for n in reader.fieldnames or []}
        if not {"date", "amount", "category"} <= names:
            raise ValueError("the CSV needs columns date, amount and category")
        for number, raw in enumerate(reader, 2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
            try:
                amount = Decimal(row["amount"].replace(",", ""))
                if not amount.is_finite():
                    raise InvalidOperation
                rows.append({"date": date.fromisoformat(row["date"]),
                             "amount": amount.quantize(CENT, ROUND_HALF_UP),
                             "category": row["category"].lower() or "uncategorised",
                             "note": row.get("note", "")})
            except (InvalidOperation, ValueError):
                problems.append(f"line {number}: can't read '{row.get('date')}' / "
                                f"'{row.get('amount')}'")
    return rows, problems


def previous_month(month):
    year, number = int(month[:4]), int(month[5:])
    return f"{year - 1}-12" if number == 1 else f"{year}-{number - 1:02d}"


def by_category(rows):
    totals = defaultdict(Decimal)
    for row in rows:
        totals[row["category"]] += row["amount"]
    return dict(sorted(totals.items(), key=lambda kv: (-kv[1], kv[0])))


def parse_budgets(items):
    budgets = {}
    for item in items:
        name, sep, value = item.rpartition("=")
        try:
            if not sep or not name:
                raise InvalidOperation
            budgets[name.strip().lower()] = Decimal(value)
        except InvalidOperation:
            raise ValueError(f"bad budget '{item}' (use category=amount)") from None
    return budgets


def summarise(rows, month, budgets, top):
    mine = [r for r in rows if r["date"].isoformat().startswith(month)]
    if not mine:
        return None
    totals, before = by_category(mine), by_category(
        [r for r in rows if r["date"].isoformat().startswith(previous_month(month))])
    total = sum(totals.values(), Decimal(0))
    days = calendar.monthrange(int(month[:4]), int(month[5:]))[1]
    return {"month": month, "entries": len(mine), "total": total,
            "daily_average": (total / days).quantize(CENT, ROUND_HALF_UP),
            "previous_total": sum(before.values(), Decimal(0)) if before else None,
            "categories": [{"name": n, "amount": a, "share": float(a / total * 100) if total else 0,
                            "change": a - before.get(n, Decimal(0)) if before else None}
                           for n, a in totals.items()],
            "budgets": [{"name": n, "limit": limit, "spent": totals.get(n, Decimal(0)),
                         "over": totals.get(n, Decimal(0)) - limit}
                        for n, limit in budgets.items()],
            "top": sorted(mine, key=lambda r: -r["amount"])[:top]}


def money(value, sign=False):
    return f"{value:+,.2f}" if sign else f"{value:,.2f}"


def render_text(s, markdown):
    compare = s["previous_total"] is not None
    out = [f"{'## ' if markdown else ''}Expenses for {s['month']} ({s['entries']} entries)", ""]
    if markdown:
        out += ["| Category | Amount | Share |" + (" Change |" if compare else ""),
                "|---|---|---|" + ("---|" if compare else "")]
        for c in s["categories"]:
            out.append(f"| {c['name']} | {money(c['amount'])} | {c['share']:.0f}% |"
                       + (f" {money(c['change'], True)} |" if compare else ""))
        out.append(f"| **Total** | {money(s['total'])} | 100% |"
                   + (f" {money(s['total'] - s['previous_total'], True)} |" if compare else ""))
    else:
        width = max([len(c["name"]) for c in s["categories"]] + [8])
        out.append(f"{'Category':<{width}}  {'Amount':>10}  {'Share':>5}"
                   + (f"  {'vs ' + previous_month(s['month']):>10}" if compare else ""))
        for c in s["categories"]:
            out.append(f"{c['name']:<{width}}  {money(c['amount']):>10}  {c['share']:>4.0f}%"
                       + (f"  {money(c['change'], True):>10}" if compare else ""))
        out.append(f"{'Total':<{width}}  {money(s['total']):>10}"
                   + " " * 7 + (f"  {money(s['total'] - s['previous_total'], True):>10}"
                                if compare else ""))
    out.append(f"\nDaily average: {money(s['daily_average'])}")
    if s["top"]:
        out.append("Biggest expenses:")
        out += [f"  {r['date']}  {money(r['amount']):>9}  {r['category']}"
                + (f" - {r['note']}" if r["note"] else "") for r in s["top"]]
    if s["budgets"]:
        out.append("Budgets:")
        for b in s["budgets"]:
            state = (f"OVER by {money(b['over'])}" if b["over"] > 0
                     else f"{money(-b['over'])} left")
            out.append(f"  {b['name']}: {money(b['spent'])} of {money(b['limit'])} ({state})")
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Monthly expense summary from a CSV.")
    parser.add_argument("csv", type=Path, help="CSV with date, amount, category and optional note")
    parser.add_argument("--month", help="YYYY-MM to summarise (default: the latest month)")
    parser.add_argument("--budget", action="append", default=[], metavar="CATEGORY=AMOUNT",
                        help="monthly budget for a category (repeatable)")
    parser.add_argument("--top", type=int, default=3, help="biggest expenses to list (3)")
    parser.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    args = parser.parse_args(argv)
    if args.top < 0:
        parser.error("--top can't be negative")
    if args.month:
        try:
            date.fromisoformat(args.month + "-01")
        except ValueError:
            parser.error(f"--month must look like 2026-11, got '{args.month}'")
    try:
        budgets = parse_budgets(args.budget)
    except ValueError as err:
        parser.error(str(err))
    try:
        rows, problems = read_expenses(args.csv)
    except (OSError, ValueError, UnicodeDecodeError) as err:
        print(f"Can't read the expenses: {err}", file=sys.stderr)
        return 1
    for problem in problems[:5]:
        print(f"Skipped {problem}", file=sys.stderr)
    month = args.month or (max(r["date"] for r in rows).strftime("%Y-%m") if rows else None)
    summary = summarise(rows, month, budgets, args.top) if month else None
    if not summary:
        print(f"No expenses found for {month or 'that file'}.", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(summary, indent=1, default=lambda v: str(v) if not hasattr(v, "isoformat")
                         else v.isoformat()))
    else:
        print(render_text(summary, args.format == "markdown"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
