"""Profile a CSV dataset: types, missing values, unique counts and value distributions."""
import argparse
import csv
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

NULLS = {"", "na", "n/a", "null", "none", "nan", "-", "?"}


def is_null(text):
    return text.strip().lower() in NULLS


def guess_type(values):
    """int, float, date, bool or text, based on the non-missing values."""
    if not values:
        return "empty"
    if all(_int(v) for v in values):
        return "int"
    if all(_float(v) for v in values):
        return "float"
    if all(v.lower() in ("true", "false", "yes", "no") for v in values):
        return "bool"
    if all(_date(v) for v in values):
        return "date"
    return "text"


def _int(text):
    try:
        int(text)
    except ValueError:
        return False
    return True


def _float(text):
    try:
        float(text)
    except ValueError:
        return False
    return True


def _date(text):
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            datetime.strptime(text, fmt)
            return True
        except ValueError:
            continue
    return False


def histogram(numbers, bins):
    low, high = min(numbers), max(numbers)
    if low == high:
        return [(low, high, len(numbers))]
    width = (high - low) / bins
    counts = [0] * bins
    for number in numbers:
        counts[min(int((number - low) / width), bins - 1)] += 1
    return [(low + i * width, low + (i + 1) * width, c) for i, c in enumerate(counts)]


def profile_column(name, raw, top, bins):
    """Return a dict of facts and a list of warnings for one column."""
    values = [v.strip() for v in raw if not is_null(v)]
    kind = guess_type(values)
    info = {"name": name, "type": kind, "rows": len(raw), "missing": len(raw) - len(values),
            "unique": len(set(values)), "top": Counter(values).most_common(top)}
    warnings = []
    if kind in ("int", "float"):
        numbers = [float(v) for v in values]
        quartiles = statistics.quantiles(numbers, n=4) if len(numbers) > 1 else [numbers[0]] * 3
        info.update(min=min(numbers), max=max(numbers), mean=statistics.fmean(numbers),
                    median=statistics.median(numbers), p25=quartiles[0], p75=quartiles[2],
                    std=statistics.stdev(numbers) if len(numbers) > 1 else 0.0,
                    bins=histogram(numbers, bins))
    elif kind == "text" and values:
        lengths = [len(v) for v in values]
        info.update(min_len=min(lengths), max_len=max(lengths),
                    avg_len=sum(lengths) / len(lengths))
        numeric = sum(_float(v) for v in values)
        if numeric >= 0.8 * len(values) and numeric < len(values):
            odd = [v for v in values if not _float(v)][:3]
            warnings.append(f"mostly numbers but has other text, e.g. {', '.join(odd)}")
    if raw and info["missing"] / len(raw) > 0.2:
        warnings.append(f"{100 * info['missing'] // len(raw)}% of values are missing")
    if len(values) > 1 and info["unique"] == 1:
        warnings.append("every value is the same")
    if len(values) == len(raw) and len(raw) > 1 and info["unique"] == len(values):
        warnings.append("all values are unique (looks like an identifier)")
    return info, warnings


def fmt(number):
    return f"{number:,.0f}" if abs(number) >= 1000 or number == int(number) else f"{number:,.2f}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Profile a CSV dataset.")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--columns", help="only these columns, comma-separated")
    parser.add_argument("--top", type=int, default=5, help="most common values to show (5)")
    parser.add_argument("--bins", type=int, default=6, help="histogram bars for numbers (6)")
    parser.add_argument("--delimiter", default=",", help="field separator (,)")
    args = parser.parse_args(argv)
    if not args.csv.is_file():
        parser.error(f"not a file: {args.csv}")
    if args.top < 1 or args.bins < 1:
        parser.error("--top and --bins must be at least 1")

    with args.csv.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle, delimiter=args.delimiter)
        header = [h.strip() for h in next(reader, [])]
        rows = [r + [""] * (len(header) - len(r)) for r in reader if r]
    if not header or not rows:
        print("No data rows found.", file=sys.stderr)
        return 1
    wanted = [c.strip() for c in args.columns.split(",")] if args.columns else header
    unknown = [c for c in wanted if c not in header]
    if unknown:
        parser.error(f"no such column: {', '.join(unknown)}")

    duplicates = len(rows) - len({tuple(r) for r in rows})
    print(f"{args.csv.name}: {len(rows)} rows x {len(header)} columns, {duplicates} duplicate "
          f"row(s)\n")
    flagged = 0
    for name in wanted:
        index = header.index(name)
        info, warnings = profile_column(name, [r[index] for r in rows], args.top, args.bins)
        print(f"{name}  [{info['type']}]  {info['rows'] - info['missing']} values, "
              f"{info['missing']} missing, {info['unique']} unique")
        if "mean" in info:
            facts = [("min", "min"), ("p25", "p25"), ("median", "median"), ("p75", "p75"),
                     ("max", "max"), ("mean", "mean"), ("std", "std")]
            print("    " + "  ".join(f"{label} {fmt(info[key])}" for label, key in facts))
            peak = max(c for _, _, c in info["bins"])
            for low, high, count in info["bins"]:
                bar = "#" * max(1 if count else 0, round(20 * count / peak))
                print(f"    {fmt(low):>9} - {fmt(high):<9} {bar:<20} {count}")
        elif info["type"] == "text" and "avg_len" in info:
            print(f"    length {info['min_len']}-{info['max_len']} (average {info['avg_len']:.1f})")
        numeric = info["type"] in ("int", "float")
        if info["top"] and (not numeric or info["unique"] <= args.top):
            print("    common: " + ", ".join(f"{v} ({c})" for v, c in info["top"]))
        for warning in warnings:
            print(f"    ! {warning}")
        flagged += bool(warnings)
        print()
    print(f"{flagged} of {len(wanted)} column(s) have something worth a look.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
