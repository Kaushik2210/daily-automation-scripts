"""Print compact sparklines (tiny inline charts) from numbers, a text file or CSV columns."""
import argparse
import csv
import re
import sys
from pathlib import Path

STYLES = {"unicode": "▁▂▃▄▅▆▇█", "ascii": "_.-:=+*#"}


def parse_numbers(text):
    """Numbers separated by spaces, commas or newlines; anything else is an error."""
    values = []
    for token in re.split(r"[\s,;]+", text.strip()):
        if token:
            values.append(float(token))
    return values


def resample(values, width):
    """Average the values into at most `width` buckets so long series fit on one line."""
    if width <= 0 or len(values) <= width:
        return list(values)
    out = []
    for i in range(width):
        chunk = values[i * len(values) // width:(i + 1) * len(values) // width]
        out.append(sum(chunk) / len(chunk))
    return out


def sparkline(values, glyphs, low=None, high=None):
    low = min(values) if low is None else low
    high = max(values) if high is None else high
    if high <= low:
        return glyphs[len(glyphs) // 2] * len(values)  # a flat line sits in the middle
    top = len(glyphs) - 1
    return "".join(glyphs[max(0, min(top, round((v - low) / (high - low) * top)))]
                   for v in values)


def short(value):
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:,.2f}".rstrip("0").rstrip(".")


def stats(values):
    first, last = values[0], values[-1]
    change = f" ({(last - first) / abs(first) * 100:+.1f}%)" if first else ""
    return f"min {short(min(values))}  max {short(max(values))}  last {short(last)}{change}"


def read_columns(path, columns):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in columns if c not in (reader.fieldnames or [])]
        if missing:
            raise KeyError(f"no column '{missing[0]}' (columns are: "
                           f"{', '.join(reader.fieldnames or [])})")
        series = {c: [] for c in columns}
        for row in reader:
            for column in columns:
                try:
                    series[column].append(float((row[column] or "").replace(",", "")))
                except ValueError:
                    continue
    return series


def pick_style(requested):
    if requested != "auto":
        return requested
    try:
        STYLES["unicode"].encode(sys.stdout.encoding or "ascii")
        return "unicode"
    except (UnicodeEncodeError, LookupError):
        return "ascii"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print sparklines from numbers.")
    parser.add_argument("numbers", nargs="*", type=float, help="the numbers to draw")
    parser.add_argument("--from-file", type=Path, dest="source",
                        help="text file of numbers separated by spaces, commas or lines")
    parser.add_argument("--csv", type=Path, help="CSV file to read columns from")
    parser.add_argument("--column", action="append", default=[], metavar="NAME",
                        help="CSV column to draw (repeat for several)")
    parser.add_argument("--width", type=int, default=0, help="shrink longer series to this width")
    parser.add_argument("--min", type=float, dest="low", help="fixed bottom of the scale")
    parser.add_argument("--max", type=float, dest="high", help="fixed top of the scale")
    parser.add_argument("--stats", action="store_true", help="add min, max, last and change")
    parser.add_argument("--style", choices=["auto", "unicode", "ascii"], default="auto")
    args = parser.parse_args(argv)
    if args.csv and not args.column:
        parser.error("--csv needs at least one --column")
    if args.column and not args.csv:
        parser.error("--column needs --csv")
    if args.width < 0:
        parser.error("--width can't be negative")

    series = {}
    try:
        if args.numbers:
            series["numbers"] = list(args.numbers)
        if args.source:
            series[args.source.stem] = parse_numbers(args.source.read_text(encoding="utf-8"))
        if args.csv:
            series.update(read_columns(args.csv, args.column))
    except (OSError, ValueError, KeyError, UnicodeDecodeError) as err:
        print(f"Can't read the numbers: {err.args[0] if isinstance(err, KeyError) else err}",
              file=sys.stderr)
        return 1
    series = {name: values for name, values in series.items() if values}
    if not series:
        parser.error("give some numbers, --from-file, or --csv with --column")

    glyphs = STYLES[pick_style(args.style)]
    pad = max(len(name) for name in series)
    for name, values in series.items():
        line = sparkline(resample(values, args.width), glyphs, args.low, args.high)
        print(f"{name:<{pad}}  {line}" + (f"  {stats(values)}" if args.stats else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
