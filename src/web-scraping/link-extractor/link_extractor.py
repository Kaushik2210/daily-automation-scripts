"""List the links on a web page (a URL or a saved .html file), sorted into internal and external."""
import argparse
import sys
import urllib.error  # web-ok: the network is only used when you give a URL
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit

USER_AGENT = "daily-automation-scripts/1.0 (link extractor)"
SKIPPED_SCHEMES = ("mailto", "tel", "javascript", "data", "sms")
MAX_BYTES = 2 * 1024 * 1024


class LinkParser(HTMLParser):
    """Collect (href, visible text, rel) for every <a href> in the page."""

    def __init__(self):
        super().__init__()
        self.links, self._current, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self._current = {"href": attrs["href"].strip(), "rel": attrs.get("rel") or ""}
            self._text = []

    def handle_data(self, data):
        if self._current is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._current is not None:
            self._current["text"] = " ".join("".join(self._text).split())
            self.links.append(self._current)
            self._current = None


def extract_links(html, base=""):
    """Return unique links as dicts: url, text, kind ('internal'|'external'), nofollow."""
    parser = LinkParser()
    parser.feed(html)
    host = urlsplit(base).netloc.lower()
    found, seen = [], set()
    for link in parser.links:
        href = link["href"]
        scheme = urlsplit(href).scheme.lower()
        if scheme in SKIPPED_SCHEMES or href.startswith("#"):
            continue
        url, _ = urldefrag(urljoin(base, href))
        if url in seen:
            continue
        seen.add(url)
        link_host = urlsplit(url).netloc.lower()
        external = bool(host and link_host and link_host != host) or (
            not host and bool(link_host))
        found.append({"url": url, "text": link["text"],
                      "kind": "external" if external else "internal",
                      "nofollow": "nofollow" in link["rel"].lower()})
    return found


def fetch_html(url, timeout=15):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(MAX_BYTES).decode(charset, errors="replace")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract the links from a web page.")
    parser.add_argument("source", help="a page URL, or a saved .html file")
    parser.add_argument("--base", default="", help="page address, to resolve links in a saved file")
    parser.add_argument("--only", choices=["internal", "external"], help="show only one kind")
    args = parser.parse_args(argv)

    path = Path(args.source)
    base = args.base
    try:
        if "://" not in args.source and path.is_file():
            html = path.read_text(encoding="utf-8", errors="replace")
        elif "://" in args.source:
            html, base = fetch_html(args.source), base or args.source
        else:
            parser.error(f"not a URL or a file: {args.source}")
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't load {args.source}: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    links = [link for link in extract_links(html, base) if args.only in (None, link["kind"])]
    for link in links:
        flag = " [nofollow]" if link["nofollow"] else ""
        print(f"{link['kind']:<9} {link['url']}  {link['text'][:40]!r}{flag}")
    external = sum(link["kind"] == "external" for link in links)
    print(f"{len(links)} unique link(s): {len(links) - external} internal, {external} external.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
