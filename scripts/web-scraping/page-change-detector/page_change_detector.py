"""Check whether a page's visible content has changed since the last time you looked."""
import argparse
import difflib
import hashlib
import json
import re
import sys
import urllib.error  # web-ok: the network is only used when you give a URL
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

USER_AGENT = "daily-automation-scripts/1.0 (page change detector)"
MAX_BYTES = 5 * 1024 * 1024
BLOCKS = {"p", "div", "li", "ul", "ol", "tr", "br", "h1", "h2", "h3", "h4", "h5", "h6", "section",
          "article", "header", "footer", "nav", "main", "table", "title", "dd", "dt", "pre"}
SKIPPED = {"script", "style", "noscript", "template"}


class TextLines(HTMLParser):
    """Turn a page into lines of visible text, one per block of content."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self._parts, self._skip = [], [], 0

    def _flush(self):
        line = " ".join("".join(self._parts).split())
        if line:
            self.lines.append(line)
        self._parts = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIPPED:
            self._skip += 1
        if tag in BLOCKS:
            self._flush()

    def handle_endtag(self, tag):
        if tag in SKIPPED and self._skip:
            self._skip -= 1
        if tag in BLOCKS:
            self._flush()

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)


def visible_lines(html, ignore=None):
    parser = TextLines()
    parser.feed(html)
    parser._flush()
    lines = parser.lines
    if ignore:
        lines = [re.sub(ignore, "", line).strip() for line in lines]
    return [line for line in lines if line]


def fingerprint(lines):
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def compare(old_lines, new_lines):
    """Return (added, removed) lists of lines, ignoring changes in order only."""
    diff = list(difflib.ndiff(old_lines, new_lines))
    added = [d[2:] for d in diff if d.startswith("+ ")]
    removed = [d[2:] for d in diff if d.startswith("- ")]
    return added, removed


def fetch_html(url, timeout=15):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(MAX_BYTES).decode(charset, errors="replace")


def load_source(source):
    path = Path(source)
    if "://" not in source and path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    if "://" in source:
        return fetch_html(source)
    raise ValueError(f"not a URL or a file: {source}")


def report(added, removed, limit=15):
    print(f"CHANGED: {len(added)} line(s) added, {len(removed)} removed.")
    shown = [f"  - {line}" for line in removed] + [f"  + {line}" for line in added]
    for line in shown[:limit]:
        print(line[:140])
    if len(shown) > limit:
        print(f"  ... and {len(shown) - limit} more")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Detect when a page's content changes.")
    parser.add_argument("source", help="a page URL, or a saved .html file")
    parser.add_argument("--state", type=Path, help="JSON file that remembers the last version")
    parser.add_argument("--previous", help="compare with this earlier saved page instead")
    parser.add_argument("--ignore", help="regex for text to ignore, e.g. dates or visitor counts")
    parser.add_argument("--no-update", action="store_true", help="keep the old baseline")
    args = parser.parse_args(argv)
    if not (args.state or args.previous):
        parser.error("give --state FILE (remember between runs) or --previous PAGE")
    try:
        if args.ignore:
            re.compile(args.ignore)
        new_lines = visible_lines(load_source(args.source), args.ignore)
        old_lines = None
        if args.previous:
            old_lines = visible_lines(load_source(args.previous), args.ignore)
        elif args.state.is_file():
            old_lines = json.loads(args.state.read_text(encoding="utf-8"))["lines"]
    except (urllib.error.URLError, OSError, ValueError, KeyError, re.error) as err:
        print(f"Couldn't check {args.source}: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    changed = False
    if old_lines is None:
        print(f"First look: saved a baseline of {len(new_lines)} line(s).")
    elif fingerprint(old_lines) == fingerprint(new_lines):
        print("No change.")
    else:
        changed = True
        report(*compare(old_lines, new_lines))
    if args.state and not args.no_update and (old_lines is None or changed):
        snapshot = {"source": args.source, "checked": datetime.now().isoformat(timespec="seconds"),
                    "hash": fingerprint(new_lines), "lines": new_lines}
        args.state.write_text(json.dumps(snapshot, indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
