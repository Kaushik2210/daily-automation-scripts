"""Read a product price from a page, keep a history in a CSV and flag price drops."""
import argparse
import csv
import json
import re
import sys
import urllib.error  # web-ok: the network is only used when you give a URL
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

USER_AGENT = "daily-automation-scripts/1.0 (price tracker)"
MAX_BYTES = 2 * 1024 * 1024
HEADER = ["timestamp", "url", "price", "currency"]
PRICE_META = {"product:price:amount", "og:price:amount", "product:sale_price:amount", "price"}
CURRENCY_META = {"product:price:currency", "og:price:currency"}
SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY"}
MONEY = re.compile(r"([$€£₹¥])\s?(\d(?:[\d.,]*\d)?)")


def parse_amount(text):
    """Turn '1,299.00', '1.299,00' or '79.99' into a float. Returns None if unreadable."""
    text = re.sub(r"[^\d.,]", "", str(text))
    if not re.search(r"\d", text):
        return None
    if "," in text and "." in text:
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
    elif "," in text:
        decimal = "," if re.search(r",\d{1,2}$", text) else ""
    else:
        decimal = "." if re.search(r"\.\d{1,2}$", text) else ""
    whole, _, cents = text.rpartition(decimal) if decimal else (text, "", "")
    whole = re.sub(r"[.,]", "", whole)
    try:
        return float(f"{whole}.{cents}" if decimal else whole)
    except ValueError:
        return None


class PriceParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metas, self.itemprops, self.ld_json = {}, [], []
        self._in_ld, self._itemprop = False, None

    def handle_starttag(self, tag, attrs):
        attrs = {k: v or "" for k, v in attrs}
        if tag == "meta":
            key = attrs.get("property") or attrs.get("name") or attrs.get("itemprop")
            if key:
                self.metas[key.lower()] = attrs.get("content", "")
        elif tag == "script" and "ld+json" in attrs.get("type", ""):
            self._in_ld = True
            self.ld_json.append("")
        if attrs.get("itemprop") == "price" and tag != "meta":
            if attrs.get("content"):
                self.itemprops.append(attrs["content"])
            else:
                self._itemprop = []

    def handle_data(self, data):
        if self._in_ld:
            self.ld_json[-1] += data
        elif self._itemprop is not None:
            self._itemprop.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_ld = False
        elif self._itemprop is not None:
            self.itemprops.append("".join(self._itemprop))
            self._itemprop = None


def find_ld_price(data):
    """Look through JSON-LD data for the first offer price and currency."""
    if isinstance(data, dict):
        for key in ("price", "lowPrice"):
            if key in data and parse_amount(data[key]) is not None:
                return parse_amount(data[key]), str(data.get("priceCurrency", ""))
        data = list(data.values())
    if isinstance(data, list):
        for item in data:
            found = find_ld_price(item)
            if found:
                return found
    return None


def extract_price(html, regex=None):
    """Return (price, currency, where it was found) or None."""
    parser = PriceParser()
    parser.feed(html)
    for block in parser.ld_json:
        try:
            found = find_ld_price(json.loads(block))
        except ValueError:
            continue
        if found:
            return found[0], found[1], "structured data"
    currency = next((parser.metas[k] for k in CURRENCY_META if k in parser.metas), "")
    for key in PRICE_META:
        if parse_amount(parser.metas.get(key, "")) is not None:
            return parse_amount(parser.metas[key]), currency, "meta tag"
    for value in parser.itemprops:
        if parse_amount(value) is not None:
            return parse_amount(value), currency, "itemprop"
    if regex:
        match = re.search(regex, html)
        if match and parse_amount(match.group(match.lastindex or 0)) is not None:
            return parse_amount(match.group(match.lastindex or 0)), currency, "your pattern"
    match = MONEY.search(re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.DOTALL))
    if match and parse_amount(match.group(2)) is not None:
        return parse_amount(match.group(2)), SYMBOLS[match.group(1)], "first price on page"
    return None


def read_history(path, url):
    if not path or not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [(r["timestamp"], float(r["price"])) for r in csv.DictReader(handle)
                if r.get("url") == url and parse_amount(r.get("price", "")) is not None]


def record(path, url, price, currency, now):
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if new:
            writer.writerow(HEADER)
        writer.writerow([now.strftime("%Y-%m-%d %H:%M:%S"), url, f"{price:.2f}", currency])


def describe(price, currency, history, target=None):
    """Lines that explain the current price against what was seen before."""
    lines = [f"Price now: {price:.2f} {currency}".rstrip()]
    if history:
        when, last = history[-1]
        diff = price - last
        pct = abs(diff) / last * 100 if last else 0
        if diff < 0:
            lines.append(f"PRICE DROP: {abs(diff):.2f} less than {last:.2f} on {when[:10]} "
                         f"({pct:.1f}%)")
        elif diff > 0:
            lines.append(f"Price rose by {diff:.2f} since {when[:10]} ({last:.2f}, {pct:.1f}%)")
        else:
            lines.append(f"Unchanged since {when[:10]}.")
        lowest = min(p for _, p in history)
        lines.append("Lowest price seen so far!" if price <= lowest
                     else f"Lowest seen: {lowest:.2f} ({len(history)} earlier reading(s))")
    else:
        lines.append("First reading for this page.")
    if target is not None and price <= target:
        lines.append(f"At or below your target of {target:.2f}.")
    return lines


def fetch_html(url, timeout=15):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(MAX_BYTES).decode(charset, errors="replace")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Track a product price over time.")
    parser.add_argument("source", help="a product page URL, or a saved .html file")
    parser.add_argument("--history", type=Path, help="CSV file that keeps the price history")
    parser.add_argument("--no-record", action="store_true", help="compare only, don't add a row")
    parser.add_argument("--target", type=float, help="tell me when the price is at or below this")
    parser.add_argument("--regex", help="pattern with one group that captures the price")
    args = parser.parse_args(argv)

    try:
        path = Path(args.source)
        html = (path.read_text(encoding="utf-8", errors="replace")
                if "://" not in args.source and path.is_file() else fetch_html(args.source))
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't load {args.source}: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    try:
        found = extract_price(html, args.regex)
    except re.error as err:
        parser.error(f"bad --regex: {err}")
    if not found:
        print("Couldn't find a price on that page. Try --regex 'Price: ([\\d.]+)'.")
        return 1
    price, currency, where = found
    print("\n".join(describe(price, currency, read_history(args.history, args.source),
                              args.target)))
    print(f"(read from {where})")
    if args.history and not args.no_record:
        record(args.history, args.source, price, currency, datetime.now())
        print(f"Saved to {args.history}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
