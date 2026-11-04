"""Log expenses to a CSV file and see totals by category. Money is handled exactly."""
import argparse
import csv
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

DEFAULT_FILE = Path.home() / "expenses.csv"
HEADER = ["date", "amount", "category", "note"]


def read_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def append_row(path, row):
    is_new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def parse_amount(text):
    try:
        value = Decimal(text.replace(",", "").lstrip("$£€"))
    except InvalidOperation:
        raise ValueError(f"'{text}' is not an amount") from None
    if value <= 0:
        raise ValueError("the amount must be more than zero")
    return value.quantize(Decimal("0.01"))


def in_month(rows, month):
    return [r for r in rows if not month or r["date"].startswith(month)]


def totals(rows):
    """Return ({category: total}, grand_total) using exact decimals."""
    by_category = defaultdict(Decimal)
    for row in rows:
        by_category[row["category"]] += Decimal(row["amount"])
    ordered = dict(sorted(by_category.items(), key=lambda kv: (-kv[1], kv[0])))
    return ordered, sum(ordered.values(), Decimal(0))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Log expenses and summarize them.")
    parser.add_argument("action", choices=["add", "list", "summary"])
    parser.add_argument("text", nargs="*", help="for add: AMOUNT CATEGORY [NOTE ...]")
    parser.add_argument("--month", help="only this month, YYYY-MM (list and summary)")
    parser.add_argument("--date", help="date for a new expense, YYYY-MM-DD (default: today)")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE,
                        help=f"CSV file (default: {DEFAULT_FILE})")
    args = parser.parse_args(argv)

    if args.action == "add":
        if len(args.text) < 2:
            parser.error("add needs an amount and a category, e.g. add 4.50 coffee latte")
        try:
            amount = parse_amount(args.text[0])
            day = date.fromisoformat(args.date) if args.date else date.today()
        except ValueError as err:
            parser.error(str(err))
        append_row(args.file, {"date": day.isoformat(), "amount": amount,
                               "category": args.text[1].lower(), "note": " ".join(args.text[2:])})
        print(f"Logged {amount} on {day} under {args.text[1].lower()}.")
        return 0

    rows = in_month(read_rows(args.file), args.month)
    if not rows:
        print("No expenses found.")
        return 0
    if args.action == "list":
        for r in sorted(rows, key=lambda r: r["date"]):
            print(f"{r['date']}  {Decimal(r['amount']):>9}  {r['category']:<12}{r['note']}")
        print(f"{len(rows)} expense(s).")
        return 0
    by_category, grand = totals(rows)
    for category, total in by_category.items():
        bar = "#" * max(1, round(20 * total / grand))
        print(f"{category:<12}{total:>10}  {bar}")
    print(f"{'total':<12}{grand:>10}  ({len(rows)} expenses)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
