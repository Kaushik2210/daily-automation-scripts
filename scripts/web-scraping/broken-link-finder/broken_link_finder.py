"""Find broken links on a web page: it reads the page, then checks every link on it."""
import argparse
import sys
import time
import urllib.error  # web-ok: the network is only used when you don't pass --plan
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit

USER_AGENT = "daily-automation-scripts/1.0 (broken link finder)"
SKIPPED = ("mailto", "tel", "javascript", "data", "sms")


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href")
        if tag == "a" and href:
            self.hrefs.append(href.strip())


def links_on_page(html, base):
    """Unique absolute http(s) links, in page order."""
    parser = Anchors()
    parser.feed(html)
    found, seen = [], set()
    for href in parser.hrefs:
        if href.startswith("#") or urlsplit(href).scheme.lower() in SKIPPED:
            continue
        url, _ = urldefrag(urljoin(base, href))
        if urlsplit(url).scheme in ("http", "https") and url not in seen:
            seen.add(url)
            found.append(url)
    return found


def is_internal(url, base):
    return urlsplit(url).netloc.lower() == urlsplit(base).netloc.lower()


def check(url, timeout=10):
    """Return (status or None, error text); HEAD first, GET if the server refuses HEAD."""
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, ""
        except urllib.error.HTTPError as err:
            if method == "HEAD" and err.code in (403, 405, 501):
                continue
            return err.code, ""
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as err:
            return None, str(getattr(err, "reason", err))
    return None, "no response"


def load_page(source, timeout=15):
    if "://" in source:
        request = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read(2 * 1024 * 1024).decode(charset, errors="replace")
    return Path(source).read_text(encoding="utf-8", errors="replace")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find broken links on a page.")
    parser.add_argument("page", help="page URL, or a saved .html file (use --base with a file)")
    parser.add_argument("--base", default="", help="the page's address, to resolve relative links")
    parser.add_argument("--only", choices=["internal", "external"], help="check only one kind")
    parser.add_argument("--max", type=int, default=100, help="most links to check (100)")
    parser.add_argument("--plan", action="store_true",
                        help="only list the links that would be checked (no requests)")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="seconds to wait between requests, to be gentle on small sites")
    args = parser.parse_args(argv)

    base = args.base or (args.page if "://" in args.page else "")
    if not base:
        parser.error("a saved file needs --base, for example --base https://example.com/")
    try:
        links = links_on_page(load_page(args.page), base)
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't load {args.page}: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    if args.only:
        links = [u for u in links if is_internal(u, base) == (args.only == "internal")]
    skipped = max(len(links) - args.max, 0)
    links = links[: args.max]

    if args.plan:
        for url in links:
            print(f"WOULD CHECK  {url}")
        print(f"Would check {len(links)} link(s) found on {args.page}.")
        return 0

    def run(url):
        if args.delay:
            time.sleep(args.delay)
        return url, *check(url)

    with ThreadPoolExecutor(max_workers=1 if args.delay else 6) as pool:
        results = list(pool.map(run, links))
    broken = [(url, status, error) for url, status, error in results
              if status is None or status >= 400]
    for url, status, error in broken:
        print(f"BROKEN  {status or error}  {url}")
    print(f"{len(results)} link(s) checked, {len(broken)} broken"
          + (f", {skipped} not checked (over --max)." if skipped else "."))
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
