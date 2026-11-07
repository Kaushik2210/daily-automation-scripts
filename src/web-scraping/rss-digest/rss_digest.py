"""Turn RSS and Atom feeds into a short markdown digest of the newest items."""
import argparse
import re
import sys
import urllib.error  # web-ok: the network is only used when you give a feed URL
import urllib.request
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from xml.etree import ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"
USER_AGENT = "daily-automation-scripts/1.0 (rss digest)"
MAX_BYTES = 2 * 1024 * 1024


def parse_date(text):
    """Return a timezone-aware datetime from an RSS (RFC 822) or Atom (ISO 8601) date, or None."""
    if not text:
        return None
    text = text.strip()
    try:
        value = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        try:
            value = datetime.fromisoformat(text)
        except ValueError:
            return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def clean_summary(html, limit=160):
    text = " ".join(unescape(re.sub(r"<[^>]+>", " ", unescape(html or ""))).split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def parse_feed(xml_text):
    """Return (feed_title, [item dicts]) for an RSS 2.0 or Atom feed."""
    if "<!DOCTYPE" in xml_text or "<!ENTITY" in xml_text:
        raise ValueError("feeds with a DOCTYPE or entities are refused for safety")
    root = ET.fromstring(xml_text)
    items = []
    if root.tag == f"{ATOM}feed":
        title = (root.findtext(f"{ATOM}title") or "Untitled feed").strip()
        for entry in root.findall(f"{ATOM}entry"):
            link = entry.find(f"{ATOM}link")
            items.append({
                "title": (entry.findtext(f"{ATOM}title") or "").strip(),
                "link": link.get("href", "") if link is not None else "",
                "date": parse_date(entry.findtext(f"{ATOM}published")
                                   or entry.findtext(f"{ATOM}updated")),
                "summary": clean_summary(entry.findtext(f"{ATOM}summary")
                                         or entry.findtext(f"{ATOM}content"))})
    else:
        channel = root.find("channel")
        if channel is None:
            raise ValueError("this doesn't look like an RSS or Atom feed")
        title = (channel.findtext("title") or "Untitled feed").strip()
        for item in channel.findall("item"):
            items.append({
                "title": (item.findtext("title") or "").strip(),
                "link": (item.findtext("link") or "").strip(),
                "date": parse_date(item.findtext("pubDate")),
                "summary": clean_summary(item.findtext("description"))})
    return title, items


def build_digest(feeds, since=None, limit=5):
    """feeds: [(title, items)]. Returns markdown with the newest items per feed."""
    lines, total = [], 0
    for title, items in feeds:
        recent = [i for i in items if since is None or (i["date"] and i["date"].date() >= since)]
        recent.sort(key=lambda i: i["date"] or datetime.min.replace(tzinfo=UTC),
                    reverse=True)
        recent = recent[:limit]
        if not recent:
            continue
        lines += [f"## {title}", ""]
        for item in recent:
            when = f" ({item['date']:%Y-%m-%d})" if item["date"] else ""
            link = f" [read]({item['link']})" if item["link"] else ""
            note = f" - {item['summary']}" if item["summary"] else ""
            lines.append(f"- **{item['title'] or 'Untitled'}**{when}{note}{link}")
        lines.append("")
        total += len(recent)
    header = f"# Feed digest ({total} item(s) from {len(feeds)} feed(s))"
    return "\n".join([header, "", *lines]).rstrip() + "\n"


def load_feed(source):
    if "://" in source:
        request = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read(MAX_BYTES).decode("utf-8", errors="replace")
    return Path(source).read_text(encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Make a markdown digest from feeds.")
    parser.add_argument("feeds", nargs="+", help="feed URLs or saved feed files")
    parser.add_argument("--since", help="only items on or after this date, YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=5, help="newest items per feed (5)")
    parser.add_argument("-o", "--output", type=Path, help="save the digest to this file")
    parser.add_argument("--apply", action="store_true",
                        help="really write --output (default only prints the digest)")
    args = parser.parse_args(argv)
    try:
        since = date.fromisoformat(args.since) if args.since else None
    except ValueError:
        parser.error("--since must look like 2026-01-01")

    loaded, status = [], 0
    for source in args.feeds:
        try:
            loaded.append(parse_feed(load_feed(source)))
        except (urllib.error.URLError, OSError, ET.ParseError, ValueError) as err:
            print(f"Skipped {source}: {getattr(err, 'reason', err)}", file=sys.stderr)
            status = 1
    digest = build_digest(loaded, since, args.limit)
    if args.output and args.apply:
        if args.output.exists():
            print(f"{args.output} already exists; choose another name.", file=sys.stderr)
            return 1
        args.output.write_text(digest, encoding="utf-8")
        print(f"Wrote {args.output}.")
    else:
        print(digest, end="")
        if args.output:
            print(f"(preview only: use --apply to write {args.output})", file=sys.stderr)
    return status


if __name__ == "__main__":
    sys.exit(main())
