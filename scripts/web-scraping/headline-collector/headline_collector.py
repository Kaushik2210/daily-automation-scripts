"""Collect the headlines from news pages and (optionally) keep a running list in a CSV file."""
import argparse
import csv
import sys
import urllib.error  # web-ok: the network is only used when you give a URL
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

USER_AGENT = "daily-automation-scripts/1.0 (headline collector)"
MAX_BYTES = 3 * 1024 * 1024
HEADER = ["date", "source", "headline", "url"]


class HeadingParser(HTMLParser):
    """Find h1-h6 headings with their text and (when there is one) their link."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.headings, self._open_href, self._heading = [], "", None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            href = (attrs.get("href") or "").strip()
            if self._heading is not None and not self._heading["href"]:
                self._heading["href"] = href
            elif self._heading is None:
                self._open_href = href
        elif len(tag) == 2 and tag[0] == "h" and tag[1] in "123456":
            self._heading = {"level": int(tag[1]), "parts": [], "href": self._open_href}

    def handle_endtag(self, tag):
        if tag == "a":
            self._open_href = ""
        elif self._heading and tag == f"h{self._heading['level']}":
            text = " ".join("".join(self._heading["parts"]).split())
            self.headings.append({"level": self._heading["level"], "text": text,
                                  "href": self._heading["href"]})
            self._heading = None

    def handle_data(self, data):
        if self._heading is not None:
            self._heading["parts"].append(data)


def find_headlines(html, base="", levels=(2, 3), min_words=3):
    """Return unique headlines as dicts with 'text' and 'url' (empty if no link)."""
    parser = HeadingParser()
    parser.feed(html)
    found, seen = [], set()
    for heading in parser.headings:
        text = heading["text"]
        key = text.casefold()
        if heading["level"] not in levels or len(text.split()) < min_words or key in seen:
            continue
        seen.add(key)
        url = urljoin(base, heading["href"]) if heading["href"] else ""
        found.append({"text": text, "url": url})
    return found


def known_entries(path):
    """The (source, headline) pairs already saved in the CSV."""
    if not path.is_file():
        return set()
    with path.open(newline="", encoding="utf-8") as handle:
        return {(row.get("source"), (row.get("headline") or "").casefold())
                for row in csv.DictReader(handle)}


def save_new(path, rows):
    new_file = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if new_file:
            writer.writerow(HEADER)
        writer.writerows(rows)


def parse_levels(text):
    try:
        low, _, high = text.partition("-")
        levels = range(int(low), int(high or low) + 1)
    except ValueError:
        raise argparse.ArgumentTypeError("use a number or range like 2 or 1-3") from None
    if not levels or levels[0] < 1 or levels[-1] > 6:
        raise argparse.ArgumentTypeError("heading levels are 1 to 6")
    return tuple(levels)


def load(source):
    path = Path(source)
    if "://" not in source and path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    if "://" not in source:
        raise ValueError(f"not a URL or a file: {source}")
    request = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(MAX_BYTES).decode(charset, errors="replace")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Collect headlines from news pages.")
    parser.add_argument("sources", nargs="+", help="page URLs or saved .html files")
    parser.add_argument("--levels", type=parse_levels, default="2-3",
                        help="heading levels to take, e.g. 2-3 (default) or 1-6")
    parser.add_argument("--min-words", type=int, default=3, help="skip shorter headings (3)")
    parser.add_argument("--base", default="", help="address to resolve links in saved files")
    parser.add_argument("--out", type=Path, help="CSV file to add new headlines to")
    args = parser.parse_args(argv)

    seen = known_entries(args.out) if args.out else set()
    rows, failed, total = [], 0, 0
    for source in args.sources:
        try:
            html = load(source)
        except (urllib.error.URLError, OSError, ValueError) as err:
            print(f"{source}: couldn't load ({getattr(err, 'reason', err)})")
            failed += 1
            continue
        base = args.base or (source if "://" in source else "")
        headlines = find_headlines(html, base, args.levels, args.min_words)
        total += len(headlines)
        print(f"{source}: {len(headlines)} headline(s)")
        for item in headlines:
            fresh = (source, item["text"].casefold()) not in seen
            print(f"  {'*' if args.out and fresh else '-'} {item['text']}"
                  + (f"  <{item['url']}>" if item["url"] else ""))
            if fresh:
                rows.append([date.today().isoformat(), source, item["text"], item["url"]])
    if args.out and rows:
        save_new(args.out, rows)
        print(f"Added {len(rows)} new headline(s) to {args.out}.")
    elif args.out:
        print(f"Nothing new for {args.out}.")
    return 1 if failed or not total else 0


if __name__ == "__main__":
    sys.exit(main())
