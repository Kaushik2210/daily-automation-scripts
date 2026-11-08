"""Audit a page's title, description, Open Graph and other SEO tags."""
import argparse
import sys
import urllib.error  # web-ok: the network is only used when you give a URL
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

USER_AGENT = "daily-automation-scripts/1.0 (meta tag auditor)"
MAX_BYTES = 2 * 1024 * 1024
TITLE_RANGE, DESCRIPTION_RANGE = (30, 60), (70, 160)


class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.lang, self.canonical = "", "", ""
        self.meta, self.h1_count = {}, 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = {k: (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = attrs.get("lang", "").strip()
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            if key:
                self.meta.setdefault(key, attrs.get("content", "").strip())
        elif tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonical = attrs.get("href", "").strip()

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def length_check(label, text, low, high):
    if not text:
        return "FAIL", f"{label}: missing"
    size = len(text)
    if size < low:
        return "WARN", f"{label}: only {size} characters (aim for {low}-{high})"
    if size > high:
        return "WARN", f"{label}: {size} characters, may be cut off (aim for {low}-{high})"
    return "ok", f"{label}: {size} characters"


def presence(label, value, level="WARN", note=""):
    if value:
        return "ok", f"{label}: {value[:60]}"
    return level, f"{label}: missing{note}"


def audit(html):
    """Return a list of (status, message) results for the page."""
    page = MetaParser()
    page.feed(html)
    meta = page.meta
    title = " ".join(page.title.split())
    results = [length_check("title", title, *TITLE_RANGE),
               length_check("meta description", meta.get("description", ""), *DESCRIPTION_RANGE),
               presence("canonical link", page.canonical),
               presence("viewport", meta.get("viewport", ""), note=" (not mobile friendly)"),
               presence("html lang", page.lang)]
    if page.h1_count == 1:
        results.append(("ok", "h1: exactly one"))
    else:
        results.append(("WARN", f"h1: found {page.h1_count}, expected exactly one"))
    if "noindex" in meta.get("robots", "").lower():
        results.append(("WARN", "robots: page tells search engines not to index it"))
    for tag in ("og:title", "og:description", "og:image", "og:url"):
        results.append(presence(tag, meta.get(tag, "")))
    results.append(presence("twitter:card", meta.get("twitter:card", "")))
    return results


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
    parser = argparse.ArgumentParser(description="Audit title, description and Open Graph tags.")
    parser.add_argument("sources", nargs="+", help="page URLs or saved .html files")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures too")
    parser.add_argument("--problems-only", action="store_true", help="hide the passing checks")
    args = parser.parse_args(argv)

    exit_code = 0
    for source in args.sources:
        try:
            results = audit(load(source))
        except (urllib.error.URLError, OSError, ValueError) as err:
            print(f"{source}: couldn't load ({getattr(err, 'reason', err)})")
            exit_code = 1
            continue
        passed = sum(status == "ok" for status, _ in results)
        print(f"{source}: {passed}/{len(results)} checks passed")
        for status, message in results:
            if status != "ok" or not args.problems_only:
                print(f"  [{status:<4}] {message}")
        failed = any(status == "FAIL" or (args.strict and status == "WARN")
                     for status, _ in results)
        exit_code = 1 if failed else exit_code
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
