"""Plot one or more CSV columns as a line or bar chart (SVG file or terminal text)."""
import argparse
import csv
import math
import sys
from html import escape
from pathlib import Path

PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9"]  # colour-blind safe


def read_series(path, x_column, y_columns):
    """Return (labels, {column: [floats]}, skipped_rows). Rows with a non-number are dropped."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        names = reader.fieldnames or []
        for column in y_columns + ([x_column] if x_column else []):
            if column not in names:
                raise KeyError(f"no column '{column}' (columns are: {', '.join(names)})")
        labels, series, skipped = [], {c: [] for c in y_columns}, 0
        for number, row in enumerate(reader, 1):
            try:
                values = {c: float(row[c].replace(",", "")) for c in y_columns}
            except (ValueError, AttributeError):
                skipped += 1
                continue
            labels.append(row[x_column] if x_column else str(number))
            for column, value in values.items():
                series[column].append(value)
    if not labels:
        raise ValueError("no rows with numbers in those columns")
    return labels, series, skipped


def nice_axis(low, high, ticks=5):
    """(min, max, step) on a 1-2-5 grid that includes zero."""
    low, high = min(low, 0.0), max(high, 0.0)
    if high == low:
        high = low + 1
    raw = (high - low) / (ticks - 1)
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    return math.floor(low / step) * step, math.ceil(high / step) * step, step


def number(value):
    return f"{value:,.2f}".rstrip("0").rstrip(".") if abs(value) < 1000 else f"{value:,.0f}"


def svg_chart(labels, series, kind, title, width, height):
    left, right, top, bottom = 64, 16, 40 if title else 16, 44
    lo, hi, step = nice_axis(min(min(v) for v in series.values()),
                             max(max(v) for v in series.values()))
    plot_w, plot_h = width - left - right, height - top - bottom

    def y(value):
        return top + plot_h * (hi - value) / (hi - lo)

    slot = plot_w / len(labels)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
           f'aria-label="{escape(title or "Chart")}" font-family="sans-serif" font-size="12">',
           f'<rect width="{width}" height="{height}" fill="#fff"/>']
    if title:
        out.append(f'<text x="{width / 2}" y="24" text-anchor="middle" font-size="16" '
                   f'font-weight="bold" fill="#111">{escape(title)}</text>')
    tick = lo
    while tick <= hi + step / 1000:
        out.append(f'<line x1="{left}" x2="{width - right}" y1="{y(tick):.1f}" y2="{y(tick):.1f}" '
                   f'stroke="#d8dce3"/><text x="{left - 8}" y="{y(tick) + 4:.1f}" '
                   f'text-anchor="end" fill="#444">{number(tick)}</text>')
        tick += step
    every = max(1, math.ceil(len(labels) / 12))  # keep the x labels readable
    for i, label in enumerate(labels):
        if i % every == 0:
            out.append(f'<text x="{left + slot * (i + .5):.1f}" y="{height - bottom + 18}" '
                       f'text-anchor="middle" fill="#444">{escape(label)}</text>')
    group = slot * 0.8 / len(series)
    for index, (name, values) in enumerate(series.items()):
        colour = PALETTE[index % len(PALETTE)]
        if kind == "bar":
            for i, value in enumerate(values):
                x = left + slot * i + slot * 0.1 + group * index
                out.append(f'<rect x="{x:.1f}" y="{min(y(value), y(0)):.1f}" width="{group:.1f}" '
                           f'height="{abs(y(value) - y(0)):.1f}" fill="{colour}">'
                           f"<title>{escape(labels[i])} ({escape(name)}): {number(value)}</title>"
                           "</rect>")
        else:
            points = [(left + slot * (i + .5), y(v)) for i, v in enumerate(values)]
            out.append(f'<polyline fill="none" stroke="{colour}" stroke-width="2.5" points="'
                       + " ".join(f"{px:.1f},{py:.1f}" for px, py in points) + '"/>')
            out += [f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{colour}"><title>'
                    f"{escape(labels[i])} ({escape(name)}): {number(values[i])}</title></circle>"
                    for i, (px, py) in enumerate(points)]
    if len(series) > 1:
        for index, name in enumerate(series):
            x = left + 110 * index
            out.append(f'<rect x="{x}" y="{height - 14}" width="10" height="10" '
                       f'fill="{PALETTE[index % len(PALETTE)]}"/><text x="{x + 15}" '
                       f'y="{height - 5}" fill="#222">{escape(name)}</text>')
    return "".join(out) + "</svg>\n"


def text_chart(labels, series, bar_width=40):
    """Horizontal bars, one block per series."""
    top = max(max(abs(v) for v in values) for values in series.values()) or 1
    wide = max(len(label) for label in labels)
    lines = []
    for name, values in series.items():
        lines.append(f"{name}")
        for label, value in zip(labels, values, strict=True):
            bar = "#" * max(1 if value else 0, round(abs(value) / top * bar_width))
            lines.append(f"  {label:<{wide}} | {'-' if value < 0 else ''}{bar} {number(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plot CSV columns as a chart.")
    parser.add_argument("csv", type=Path, help="the CSV file (with a header row)")
    parser.add_argument("--y", action="append", required=True, metavar="COLUMN",
                        help="numeric column to plot (repeat for several)")
    parser.add_argument("--x", help="column for the x axis labels (default: row number)")
    parser.add_argument("--type", choices=["line", "bar"], default="line")
    parser.add_argument("--format", choices=["svg", "text"], default="svg")
    parser.add_argument("--title", help="chart title")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=420)
    parser.add_argument("--output", type=Path, help="write this new file instead of printing")
    parser.add_argument("--force", action="store_true", help="overwrite --output if it exists")
    args = parser.parse_args(argv)
    if not (200 <= args.width <= 4000 and 150 <= args.height <= 4000):
        parser.error("--width must be 200-4000 and --height 150-4000")
    if args.output and args.output.exists() and not args.force:
        print(f"{args.output} already exists; use --force to overwrite it.", file=sys.stderr)
        return 1
    try:
        labels, series, skipped = read_series(args.csv, args.x, args.y)
    except (OSError, KeyError, ValueError, UnicodeDecodeError) as err:
        print(f"Can't plot that: {err.args[0] if isinstance(err, KeyError) else err}",
              file=sys.stderr)
        return 1
    if args.format == "text":
        text = text_chart(labels, series)
    else:
        text = svg_chart(labels, series, args.type, args.title, args.width, args.height)
    note = f" ({skipped} row(s) skipped: not a number)" if skipped else ""
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}: {len(labels)} point(s), {len(series)} series{note}")
    else:
        print(text, end="")
        if skipped:
            print(f"Note:{note}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
