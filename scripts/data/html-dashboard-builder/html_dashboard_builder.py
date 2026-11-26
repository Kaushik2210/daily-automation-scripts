"""Turn a JSON file of metrics, chart series and tables into one self-contained HTML dashboard."""
import argparse
import json
import sys
from html import escape
from pathlib import Path

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#16181d;--muted:#5b6270;--line:#dfe3ea;--accent:#2563eb;
--good:#15803d;--bad:#b91c1c}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#171a21;--ink:#eceef2;--muted:#9aa3b2;
--line:#2a2f3a;--accent:#7aa2ff;--good:#4ade80;--bad:#f87171}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.5 system-ui,sans-serif}
main{max-width:1000px;margin:0 auto;padding:24px 16px 48px}h1{margin:0;font-size:1.7rem}
.sub{color:var(--muted);margin:4px 0 24px}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.label{color:var(--muted);font-size:.9rem}.value{font-size:1.8rem;font-weight:650}
.change{font-size:.9rem;font-weight:600}.good{color:var(--good)}.bad{color:var(--bad)}
.flat{color:var(--muted)}h2{font-size:1.05rem;margin:0 0 12px}
section{margin-top:24px}svg{width:100%;height:auto;display:block}
.axis{stroke:var(--line)}.tick{fill:var(--muted);font-size:11px}.bar{fill:var(--accent)}
.line{fill:none;stroke:var(--accent);stroke-width:2.5}.dot{fill:var(--accent)}
table{border-collapse:collapse;width:100%}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--muted);font-weight:600}td.num{text-align:right}
.wrap{overflow-x:auto}
"""


def fmt(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def metric_card(metric):
    unit = str(metric.get("unit", ""))
    value = fmt(metric["value"])
    shown = f"{unit}{value}" if unit in ("$", "€", "£") else f"{value}{unit}"
    change = metric.get("change")
    note = ""
    if isinstance(change, (int, float)):
        better = change < 0 if metric.get("lower_is_better") else change > 0
        kind = "flat" if change == 0 else ("good" if better else "bad")
        arrow = "▲" if change > 0 else ("▼" if change < 0 else "●")
        note = f'<div class="change {kind}">{arrow} {abs(change):g}%</div>'
    return (f'<div class="card"><div class="label">{escape(str(metric["label"]))}</div>'
            f'<div class="value">{escape(shown)}</div>{note}</div>')


def nice_max(top):
    if top <= 0:
        return 1
    step = 10 ** (len(str(int(top))) - 1)
    return -(-top // step) * step if top >= 1 else top


def chart_svg(chart):
    labels, values = [str(x) for x in chart["labels"]], [float(v) for v in chart["values"]]
    if len(labels) != len(values) or not values:
        raise ValueError(f"chart '{chart.get('title', '?')}' needs equal, non-empty labels/values")
    width, height, left, bottom, top = 600, 240, 48, 28, 12
    ceiling = nice_max(max(max(values), 0))
    plot_w, plot_h = width - left - 8, height - bottom - top
    step = plot_w / len(values)

    def y(value):
        return top + plot_h - plot_h * value / ceiling

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="{escape(str(chart.get("title", "chart")))}">']
    for i in range(5):
        tick = ceiling * i / 4
        parts.append(f'<line class="axis" x1="{left}" x2="{width - 8}" y1="{y(tick):.1f}" '
                     f'y2="{y(tick):.1f}"/><text class="tick" x="{left - 6}" y="{y(tick) + 4:.1f}" '
                     f'text-anchor="end">{escape(fmt(round(tick, 2)))}</text>')
    points = []
    for i, (label, value) in enumerate(zip(labels, values, strict=True)):
        centre = left + step * (i + 0.5)
        title = f"<title>{escape(label)}: {escape(fmt(value))}</title>"
        if chart.get("type") == "bar":
            bar = step * 0.6
            parts.append(f'<rect class="bar" x="{centre - bar / 2:.1f}" y="{y(value):.1f}" '
                         f'width="{bar:.1f}" height="{top + plot_h - y(value):.1f}" rx="3">'
                         f"{title}</rect>")
        else:
            points.append((centre, y(value), title))
        parts.append(f'<text class="tick" x="{centre:.1f}" y="{height - 8}" '
                     f'text-anchor="middle">{escape(label)}</text>')
    if points:
        path = " ".join(f"{x:.1f},{py:.1f}" for x, py, _ in points)
        parts.append(f'<polyline class="line" points="{path}"/>')
        parts += [f'<circle class="dot" cx="{x:.1f}" cy="{py:.1f}" r="4">{t}</circle>'
                  for x, py, t in points]
    return "".join(parts) + "</svg>"


def table_html(table):
    head = "".join(f"<th scope=\"col\">{escape(str(c))}</th>" for c in table["columns"])
    rows = []
    for row in table["rows"]:
        cells = "".join(
            f'<td class="{"num" if isinstance(c, (int, float)) else ""}">{escape(fmt(c))}</td>'
            for c in row)
        rows.append(f"<tr>{cells}</tr>")
    return (f'<div class="wrap"><table><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def build(data):
    title = escape(str(data.get("title", "Dashboard")))
    body = [f"<h1>{title}</h1>"]
    if data.get("subtitle"):
        body.append(f'<p class="sub">{escape(str(data["subtitle"]))}</p>')
    if data.get("metrics"):
        cards = "".join(metric_card(m) for m in data["metrics"])
        body.append(f'<div class="grid">{cards}</div>')
    if data.get("charts"):
        body.append('<section class="grid">' + "".join(
            f'<div class="card"><h2>{escape(str(c.get("title", "")))}</h2>{chart_svg(c)}</div>'
            for c in data["charts"]) + "</section>")
    for table in data.get("tables", []):
        body.append(f'<section class="card"><h2>{escape(str(table.get("title", "")))}</h2>'
                    f"{table_html(table)}</section>")
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{title}</title><style>{CSS}</style></head>\n<body><main>"
            + "\n".join(body) + "</main></body></html>\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a static HTML dashboard from JSON.")
    parser.add_argument("data", type=Path, help="JSON with metrics, charts and tables")
    parser.add_argument("--output", type=Path, help="write this new file instead of printing")
    parser.add_argument("--force", action="store_true", help="overwrite --output if it exists")
    args = parser.parse_args(argv)
    if args.output and args.output.exists() and not args.force:
        print(f"{args.output} already exists; use --force to overwrite it.", file=sys.stderr)
        return 1
    try:
        html = build(json.loads(args.data.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as err:
        print(f"Can't build the dashboard: {type(err).__name__}: {err}", file=sys.stderr)
        return 1
    if args.output:
        args.output.write_text(html, encoding="utf-8")
        print(f"Wrote {args.output} ({len(html):,} bytes). It needs no internet connection.")
    else:
        print(html, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
