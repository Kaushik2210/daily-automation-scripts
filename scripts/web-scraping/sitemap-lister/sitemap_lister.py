"""List every URL in a sitemap.xml (a URL or a saved file), with last-modified dates."""
import argparse
import csv
import sys
import urllib.error  # web-ok: the network is only used when you give a sitemap URL
import urllib.request
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

USER_AGENT = "daily-automation-scripts/1.0 (sitemap lister)"
MAX_BYTES = 5 * 1024 * 1024


def tag_name(element):
    """The tag without its XML namespace, e.g. '{...}url' -> 'url'."""
    return element.tag.rsplit("}", 1)[-1]


def parse_sitemap(xml_text):
    """Return (kind, entries): kind is 'urlset' or 'sitemapindex'; entries are (loc, lastmod)."""
    if "<!DOCTYPE" in xml_text or "<!ENTITY" in xml_text:
        raise ValueError("sitemaps with a DOCTYPE or entities are refused for safety")
    root = ET.fromstring(xml_text.lstrip("﻿"))
    kind = tag_name(root)
    if kind not in ("urlset", "sitemapindex"):
        raise ValueError("this doesn't look like a sitemap")
    entries = []
    for child in root:
        fields = {tag_name(node): (node.text or "").strip() for node in child}
        if fields.get("loc"):
            entries.append((fields["loc"], fields.get("lastmod", "")))
    return kind, entries


def lastmod_date(text):
    """The date part of a sitemap lastmod value, or None."""
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def filter_entries(entries, contains="", newer_than=None):
    result = []
    for loc, lastmod in entries:
        if contains and contains.lower() not in loc.lower():
            continue
        if newer_than and not ((day := lastmod_date(lastmod)) and day >= newer_than):
            continue
        result.append((loc, lastmod))
    return result


def load(source):
    if "://" in source:
        request = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read(MAX_BYTES).decode("utf-8", errors="replace")
    return Path(source).read_text(encoding="utf-8-sig")


def main(argv=None):
    parser = argparse.ArgumentParser(description="List the URLs in a sitemap.")
    parser.add_argument("sitemap", help="sitemap URL or saved .xml file")
    parser.add_argument("--contains", default="", help="only URLs containing this text")
    parser.add_argument("--newer-than", help="only entries modified on or after YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=0, help="show at most this many (0 = all)")
    parser.add_argument("--csv", action="store_true", help="print CSV instead of text")
    args = parser.parse_args(argv)
    try:
        newer = date.fromisoformat(args.newer_than) if args.newer_than else None
    except ValueError:
        parser.error("--newer-than must look like 2026-01-01")

    try:
        kind, entries = parse_sitemap(load(args.sitemap))
    except (urllib.error.URLError, OSError, ET.ParseError, ValueError) as err:
        print(f"Couldn't read {args.sitemap}: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    shown = filter_entries(entries, args.contains, newer)
    if args.limit:
        shown = shown[: args.limit]
    if args.csv:
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(["url", "lastmod"])
        writer.writerows(shown)
        return 0
    label = "child sitemap(s)" if kind == "sitemapindex" else "URL(s)"
    for loc, lastmod in shown:
        print(f"{lastmod[:10] or '----------'}  {loc}")
    print(f"{len(shown)} of {len(entries)} {label}" + (
        " (this is a sitemap index: run the tool on each child sitemap)." if kind == "sitemapindex"
        else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
