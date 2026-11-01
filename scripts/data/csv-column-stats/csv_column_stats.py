"""Summarize every column of a CSV: counts, blanks, min/max/mean or top values."""
import argparse
import csv
import statistics
import sys
from collections import Counter
from pathlib import Path


def to_number(text):
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def describe_column(values):
    """Return a dict describing one column's values (strings)."""
    filled = [v.strip() for v in values if v.strip()]
    info = {"count": len(filled), "blank": len(values) - len(filled), "unique": len(set(filled))}
    numbers = [n for n in map(to_number, filled) if n is not None]
    if filled and len(numbers) == len(filled):
        info.update(kind="number", min=min(numbers), max=max(numbers),
                    mean=statistics.fmean(numbers), median=statistics.median(numbers))
    else:
        info.update(kind="text", top=Counter(filled).most_common(3))
    return info


def column_stats(rows):
    """rows[0] is the header; returns {column_name: info}."""
    if not rows:
        return {}
    header, body = rows[0], rows[1:]
    return {name: describe_column([row[i] if i < len(row) else "" for row in body])
            for i, name in enumerate(header)}


def fmt(number):
    return f"{number:.2f}".rstrip("0").rstrip(".")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Per-column statistics for a CSV file.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--delimiter", default=",")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")

    with args.file.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle, delimiter=args.delimiter))
    stats = column_stats(rows)
    print(f"{len(rows) - 1 if rows else 0} data row(s), {len(stats)} column(s)\n")
    for name, info in stats.items():
        print(f"{name}  [{info['kind']}]  filled={info['count']} blank={info['blank']} "
              f"unique={info['unique']}")
        if info["kind"] == "number":
            print(f"    min={fmt(info['min'])} max={fmt(info['max'])} "
                  f"mean={fmt(info['mean'])} median={fmt(info['median'])}")
        elif info["top"]:
            print("    top: " + ", ".join(f"{v} ({c})" for v, c in info["top"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
