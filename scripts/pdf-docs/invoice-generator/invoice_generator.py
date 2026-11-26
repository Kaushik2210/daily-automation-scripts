"""Generate a print-ready HTML invoice (or a text summary) from a JSON file."""
import argparse
import json
import sys
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from html import escape
from pathlib import Path

SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥"}
CENT = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def to_decimal(value, field):
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"{field} must be a number, got {value!r}") from None
    if not number.is_finite():
        raise ValueError(f"{field} must be a number, got {value!r}")
    return number


def calculate(data):
    """Validate the invoice and work out every amount with exact decimal arithmetic."""
    for field in ("number", "from", "to", "items"):
        if not data.get(field):
            raise ValueError(f"the invoice needs '{field}'")
    lines = []
    for position, item in enumerate(data["items"], 1):
        quantity = to_decimal(item.get("quantity", 1), f"item {position} quantity")
        price = to_decimal(item.get("unit_price"), f"item {position} unit_price")
        if quantity <= 0 or price < 0:
            raise ValueError(f"item {position}: quantity must be above 0 and price not negative")
        lines.append({"description": str(item.get("description", "")), "quantity": quantity,
                      "unit_price": money(price), "total": money(quantity * price)})
    subtotal = sum((line["total"] for line in lines), Decimal(0))
    discount = money(to_decimal(data.get("discount", 0), "discount"))
    if discount < 0 or discount > subtotal:
        raise ValueError("discount can't be negative or more than the subtotal")
    rate = to_decimal(data.get("tax_rate", 0), "tax_rate")
    if rate < 0:
        raise ValueError("tax_rate can't be negative")
    tax = money((subtotal - discount) * rate / 100)
    return {"lines": lines, "subtotal": subtotal, "discount": discount, "tax_rate": rate,
            "tax": tax, "total": subtotal - discount + tax}


def amount_text(value, currency):
    symbol = SYMBOLS.get(currency, "")
    figure = f"{value:,.2f}"
    return f"{symbol}{figure}" if symbol else f"{figure} {currency}"


def quantity_text(quantity):
    return f"{quantity:f}".rstrip("0").rstrip(".") if "." in f"{quantity:f}" else f"{quantity:f}"


def party(info):
    parts = [f"<strong>{escape(str(info.get('name', '')))}</strong>"]
    parts += [escape(str(line)) for line in info.get("address", [])]
    if info.get("email"):
        parts.append(escape(str(info["email"])))
    return "<br>".join(parts)


CSS = """
:root{--bg:#f4f5f7;--paper:#fff;--ink:#17191f;--muted:#5d6472;--line:#dde1e8;--accent:#1d4ed8}
@media (prefers-color-scheme:dark){:root{--bg:#101216;--paper:#181b21;--ink:#eceef2;
--muted:#9ba3b1;--line:#2b303a;--accent:#8fb0ff}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}
main{max-width:760px;margin:24px auto;padding:40px;background:var(--paper);
border:1px solid var(--line);border-radius:10px}
header{display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap}
h1{margin:0;font-size:2rem;color:var(--accent);letter-spacing:.04em}
.meta{text-align:right;color:var(--muted)}
.parties{display:flex;gap:48px;flex-wrap:wrap;margin:32px 0}
.label{color:var(--muted);font-size:.8rem;text-transform:uppercase;letter-spacing:.06em}
table{width:100%;border-collapse:collapse}
th,td{padding:10px 8px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--muted);font-size:.8rem;text-transform:uppercase}
.num{text-align:right;font-variant-numeric:tabular-nums}
.totals{margin:16px 0 0 auto;width:min(100%,300px)}.totals td{border:0;padding:4px 8px}
.grand td{font-weight:700;font-size:1.15rem;border-top:2px solid var(--ink)}
.notes{margin-top:32px;color:var(--muted)}
@media print{body{background:#fff;color:#000}main{border:0;margin:0;padding:0;background:#fff}}
"""


def render_html(data, figures):
    currency = str(data.get("currency", "USD")).upper()
    shown = lambda v: escape(amount_text(v, currency))  # noqa: E731
    rows = "".join(
        f"<tr><td>{escape(line['description'])}</td><td class=\"num\">"
        f"{quantity_text(line['quantity'])}</td><td class=\"num\">{shown(line['unit_price'])}</td>"
        f"<td class=\"num\">{shown(line['total'])}</td></tr>" for line in figures["lines"])
    totals = [("Subtotal", figures["subtotal"])]
    if figures["discount"]:
        totals.append(("Discount", -figures["discount"]))
    if figures["tax_rate"]:
        totals.append((f"Tax ({figures['tax_rate'].normalize():f}%)", figures["tax"]))
    totals_html = "".join(f'<tr><td>{label}</td><td class="num">{shown(value)}</td></tr>'
                          for label, value in totals)
    due = f"<br>Due {escape(str(data['due_date']))}" if data.get("due_date") else ""
    notes = f'<p class="notes">{escape(str(data["notes"]))}</p>' if data.get("notes") else ""
    number = escape(str(data["number"]))
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>Invoice {number}</title><style>{CSS}</style></head>\n<body><main>"
            f"<header><h1>INVOICE</h1><div class=\"meta\">No. {number}<br>"
            f"{escape(str(data.get('date', date.today())))}{due}</div></header>"
            f'<div class="parties"><div><div class="label">From</div>{party(data["from"])}</div>'
            f'<div><div class="label">Bill to</div>{party(data["to"])}</div></div>'
            "<table><thead><tr><th>Description</th><th class=\"num\">Qty</th>"
            "<th class=\"num\">Unit price</th><th class=\"num\">Amount</th></tr></thead>"
            f"<tbody>{rows}</tbody></table><table class=\"totals\"><tbody>{totals_html}"
            f'<tr class="grand"><td>Total due</td><td class="num">{shown(figures["total"])}</td>'
            f"</tr></tbody></table>{notes}</main></body></html>\n")


def render_text(data, figures):
    currency = str(data.get("currency", "USD")).upper()
    lines = [f"Invoice {data['number']} for {data['to'].get('name', '')}"]
    for line in figures["lines"]:
        lines.append(f"  {line['description']:<32} {quantity_text(line['quantity']):>6} x "
                     f"{amount_text(line['unit_price'], currency):>10} = "
                     f"{amount_text(line['total'], currency):>11}")
    lines.append(f"  {'Subtotal':<32} {amount_text(figures['subtotal'], currency):>32}")
    if figures["discount"]:
        lines.append(f"  {'Discount':<32} {'-' + amount_text(figures['discount'], currency):>32}")
    if figures["tax_rate"]:
        lines.append(f"  {'Tax ' + format(figures['tax_rate'].normalize(), 'f') + '%':<32} "
                     f"{amount_text(figures['tax'], currency):>32}")
    lines.append(f"  {'TOTAL DUE':<32} {amount_text(figures['total'], currency):>32}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate an HTML invoice from JSON.")
    parser.add_argument("invoice", type=Path, help="invoice JSON (see the README)")
    parser.add_argument("--format", choices=["html", "text"], default="html")
    parser.add_argument("--output", type=Path, help="write this new file instead of printing")
    parser.add_argument("--force", action="store_true", help="overwrite --output if it exists")
    args = parser.parse_args(argv)
    if args.output and args.output.exists() and not args.force:
        print(f"{args.output} already exists; use --force to overwrite it.", file=sys.stderr)
        return 1
    try:
        data = json.loads(args.invoice.read_text(encoding="utf-8"))
        figures = calculate(data)
        text = render_html(data, figures) if args.format == "html" else render_text(data, figures)
    except (OSError, ValueError, TypeError, AttributeError) as err:
        print(f"Can't make the invoice: {err}", file=sys.stderr)
        return 1
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        currency = str(data.get("currency", "USD")).upper()
        print(f"Wrote {args.output}: invoice {data['number']}, total "
              f"{amount_text(figures['total'], currency)}")
    else:
        print(text, end="" if text.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
