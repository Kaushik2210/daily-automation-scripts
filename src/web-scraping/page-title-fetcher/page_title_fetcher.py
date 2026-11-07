"""Get the title (and description) of web pages or saved .html files."""
import argparse
import csv
import sys
import urllib.error  # web-ok: the network is only used when you give a URL
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path

USER_AGENT = "daily-automation-scripts/1.0 (title fetcher)"
READ_LIMIT = 256 * 1024


class TitleParser(HTMLParser):
    """Collect the <title> text and the meta description, ignoring everything else."""

    def __init__(self):
        super().__init__()
        self.title, self.description = "", ""
        self._in_title, self._seen = False, False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = not self._seen      # only the first <title> counts
        elif tag == "meta" and (attrs.get("name") or "").lower() == "description":
            self.description = " ".join((attrs.get("content") or "").split())

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title, self._seen = False, True

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def extract(html):
    """Return (title, description) with whitespace collapsed; empty strings if missing."""
    parser = TitleParser()
    parser.feed(html)
    return " ".join(parser.title.split()), parser.description


def load(source, timeout=15):
    if "://" in source:
        request = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read(READ_LIMIT).decode(charset, errors="replace")
    return Path(source).read_text(encoding="utf-8", errors="replace")


def inspect(source):
    """Return {'source','title','description','error'} for one URL or file."""
    try:
        title, description = extract(load(source))
        return {"source": source, "title": title, "description": description, "error": ""}
    except (urllib.error.URLError, OSError, ValueError) as err:
        return {"source": source, "title": "", "description": "",
                "error": str(getattr(err, "reason", err))}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fetch page titles.")
    parser.add_argument("sources", nargs="+", help="page URLs or saved .html files")
    parser.add_argument("--description", action="store_true", help="also show the meta description")
    parser.add_argument("--csv", action="store_true", help="print CSV instead of text")
    args = parser.parse_args(argv)

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(inspect, args.sources))
    if args.csv:
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(["source", "title", "description", "error"])
        writer.writerows([r["source"], r["title"], r["description"], r["error"]] for r in results)
    else:
        for r in results:
            if r["error"]:
                print(f"ERROR  {r['source']}  ({r['error']})")
                continue
            print(f"{r['title'] or '(no title)'}  <-  {r['source']}")
            if args.description and r["description"]:
                print(f"    {r['description']}")
    failed = sum(bool(r["error"]) for r in results)
    if not args.csv:
        print(f"{len(results) - failed} of {len(results)} page(s) read.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
