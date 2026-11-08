"""Watch a careers page and report new and closed job postings."""
import argparse
import json
import re
import sys
import urllib.error  # web-ok: the network is only used when you give a URL
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin

USER_AGENT = "daily-automation-scripts/1.0 (job listing watcher)"
MAX_BYTES = 3 * 1024 * 1024
JOB_LINK = r"job|career|position|opening|vacanc|apply|role|posting"


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a" and dict(attrs).get("href"):
            self._href, self._text = dict(attrs)["href"].strip(), []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def find_jobs(html, base="", link_pattern=JOB_LINK, match=None):
    """Return {url: title} for links that look like job postings."""
    parser = LinkParser()
    parser.feed(html)
    jobs = {}
    for href, text in parser.links:
        if not text or href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        if not re.search(link_pattern, href, re.IGNORECASE):
            continue
        if match and not re.search(match, text, re.IGNORECASE):
            continue
        jobs.setdefault(urldefrag(urljoin(base, href))[0], text)
    return jobs


def compare(old, new):
    """Return (new_jobs, closed_jobs) as lists of (title, url)."""
    opened = [(title, url) for url, title in new.items() if url not in old]
    closed = [(title, url) for url, title in old.items() if url not in new]
    return opened, closed


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
    parser = argparse.ArgumentParser(description="Watch a careers page for new postings.")
    parser.add_argument("source", help="a careers page URL, or a saved .html file")
    parser.add_argument("--state", type=Path, help="JSON file that remembers the postings seen")
    parser.add_argument("--previous", help="compare with this earlier saved page instead")
    parser.add_argument("--match", help="only postings whose title matches, e.g. 'engineer|data'")
    parser.add_argument("--link-pattern", default=JOB_LINK,
                        help="regex a link address must match to count as a posting")
    parser.add_argument("--base", default="", help="page address, to resolve links in saved files")
    args = parser.parse_args(argv)
    if not (args.state or args.previous):
        parser.error("give --state FILE (remember between runs) or --previous PAGE")

    base = args.base or (args.source if "://" in args.source else "")
    try:
        for pattern in (args.match, args.link_pattern):
            if pattern:
                re.compile(pattern)
        current = find_jobs(load(args.source), base, args.link_pattern, args.match)
        old = None
        if args.previous:
            old = find_jobs(load(args.previous), base, args.link_pattern, args.match)
        elif args.state.is_file():
            old = json.loads(args.state.read_text(encoding="utf-8"))["jobs"]
    except (urllib.error.URLError, OSError, ValueError, KeyError, re.error) as err:
        print(f"Couldn't check {args.source}: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    opened = []
    if old is None:
        print(f"First look: {len(current)} posting(s) found, saved as the baseline.")
        for url, title in current.items():
            print(f"  = {title}  <{url}>")
    else:
        opened, closed = compare(old, current)
        for title, url in opened:
            print(f"  NEW     {title}  <{url}>")
        for title, _url in closed:
            print(f"  CLOSED  {title}")
        print(f"{len(opened)} new, {len(closed)} closed, "
              f"{len(current) - len(opened)} unchanged.")
    if args.state:
        snapshot = {"source": args.source, "checked": datetime.now().isoformat(timespec="seconds"),
                    "jobs": current}
        args.state.write_text(json.dumps(snapshot, indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    return 1 if opened else 0


if __name__ == "__main__":
    sys.exit(main())
