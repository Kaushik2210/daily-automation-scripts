"""Export the tables on a web page (or saved .html file) to CSV files. Dry run by default."""
import argparse
import csv
import re
import sys
import urllib.error  # web-ok: the network is only used when you give a URL
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

USER_AGENT = "daily-automation-scripts/1.0 (table extractor)"
MAX_BYTES = 5 * 1024 * 1024


class TableParser(HTMLParser):
    """Collect every <table> as a list of rows of cell text (colspans are padded out)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._stack = [], []

    def _top(self):
        return self._stack[-1] if self._stack else None

    def _close_cell(self):
        top = self._top()
        if top and top["cell"] is not None:
            text = " ".join("".join(top["cell"]).split())
            top["row"].extend([text] + [""] * (top["span"] - 1))
            top["cell"] = None

    def _close_row(self):
        self._close_cell()
        top = self._top()
        if top and top["row"]:
            top["table"]["rows"].append(top["row"])
        if top:
            top["row"] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        top = self._top()
        if tag == "table":
            table = {"id": attrs.get("id") or "", "caption": "", "rows": []}
            self.tables.append(table)
            self._stack.append({"table": table, "row": [], "cell": None, "span": 1,
                                "in_caption": False})
        elif top is None:
            return
        elif tag == "caption":
            top["in_caption"] = True
        elif tag == "tr":
            self._close_row()
        elif tag in ("td", "th"):
            self._close_cell()
            top["cell"] = []
            span = re.match(r"\d+", attrs.get("colspan") or "")
            top["span"] = min(int(span.group(0)), 50) if span else 1
        elif tag == "br" and top["cell"] is not None:
            top["cell"].append(" ")

    def handle_endtag(self, tag):
        top = self._top()
        if top is None:
            return
        if tag == "caption":
            top["in_caption"] = False
        elif tag == "tr":
            self._close_row()
        elif tag in ("td", "th"):
            self._close_cell()
        elif tag == "table":
            self._close_row()
            self._stack.pop()

    def handle_data(self, data):
        top = self._top()
        if top is None:
            return
        if top["cell"] is not None:
            top["cell"].append(data)
        elif top["in_caption"]:
            top["table"]["caption"] = " ".join((top["table"]["caption"] + data).split())


def extract_tables(html):
    parser = TableParser()
    parser.feed(html)
    parser.close()
    tables = []
    for table in parser.tables:
        width = max((len(row) for row in table["rows"]), default=0)
        if width:
            rows = [row + [""] * (width - len(row)) for row in table["rows"]]
            tables.append({**table, "rows": rows, "width": width})
    return tables


def source_stem(source):
    if "://" in source:
        parts = urlsplit(source)
        text = f"{parts.netloc}{parts.path}"
    else:
        text = Path(source).stem
    return re.sub(r"[^\w]+", "-", text).strip("-").lower()[:50] or "page"


def fetch_html(url, timeout=15):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(MAX_BYTES).decode(charset, errors="replace")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export HTML tables to CSV.")
    parser.add_argument("source", help="a page URL, or a saved .html file")
    parser.add_argument("--out-dir", type=Path, default=Path("."), help="where to write the CSVs")
    parser.add_argument("--table", type=int, action="append", metavar="N",
                        help="only this table (1 = first); repeat for several")
    parser.add_argument("--preview", type=int, default=3, help="rows to show per table (3)")
    parser.add_argument("--apply", action="store_true", help="actually write the CSV files")
    args = parser.parse_args(argv)

    path = Path(args.source)
    try:
        html = (path.read_text(encoding="utf-8", errors="replace")
                if "://" not in args.source and path.is_file() else fetch_html(args.source))
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't load {args.source}: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    tables = extract_tables(html)
    wanted = args.table or range(1, len(tables) + 1)
    chosen = [(n, tables[n - 1]) for n in wanted if 1 <= n <= len(tables)]
    if not chosen:
        print(f"No matching tables found ({len(tables)} on the page).")
        return 1
    stem, written = source_stem(args.source), 0
    for number, table in chosen:
        label = table["caption"] or table["id"] or "untitled"
        target = args.out_dir / f"{stem}-table-{number}.csv"
        print(f"Table {number} ({label}): {len(table['rows'])} row(s) x {table['width']} column(s)")
        for row in table["rows"][:max(args.preview, 0)]:
            print("   " + " | ".join(row))
        if not args.apply:
            print(f"   would write {target}")
        elif target.exists():
            print(f"   skipped, {target} already exists")
        else:
            args.out_dir.mkdir(parents=True, exist_ok=True)
            with target.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerows(table["rows"])
            print(f"   wrote {target}")
            written += 1
    if not args.apply:
        print("Dry run - nothing written. Add --apply to create the CSV files.")
    else:
        print(f"Wrote {written} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
