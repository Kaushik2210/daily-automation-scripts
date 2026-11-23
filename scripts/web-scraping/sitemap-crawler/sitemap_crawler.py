"""List a sitemap's pages, mark which ones robots.txt allows, and optionally crawl them."""
import argparse
import contextlib
import gzip
import re
import sys
import time
import urllib.error  # web-ok: the network is only used for URLs, --fetch and --follow-index
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

USER_AGENT = "daily-automation-scripts/1.0 (sitemap crawler)"
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def read_source(source, timeout=15):
    """Return the text of a local file or an http(s) URL (.gz is unpacked)."""
    if "://" not in source:
        data = Path(source).read_bytes()
    else:
        request = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read(20_000_000)
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data.decode("utf-8", errors="replace")


def parse_sitemap(text):
    """Return ('urlset', [(url, lastmod)]) or ('index', [sitemap urls])."""
    root = ET.fromstring(text)
    tag = root.tag.rsplit("}", 1)[-1]
    items = []
    for child in root:
        loc = lastmod = ""
        for part in child:
            name = part.tag.rsplit("}", 1)[-1]
            if name == "loc":
                loc = (part.text or "").strip()
            elif name == "lastmod":
                lastmod = (part.text or "").strip()
        if loc:
            items.append((loc, lastmod))
    if tag == "sitemapindex":
        return "index", [loc for loc, _ in items]
    if tag != "urlset":
        raise ValueError(f"this is not a sitemap (the root element is <{tag}>)")
    return "urlset", items


class Robots:
    """robots.txt rules as most crawlers apply them: the longest matching rule wins, and
    'Allow' beats 'Disallow' when they are equally specific (RFC 9309)."""

    def __init__(self, text):
        self.groups, self.sitemaps = [], []
        agents, rules, delay, collecting = [], [], None, False
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            field, _, value = line.partition(":")
            field, value = field.strip().lower(), value.strip()
            if field == "user-agent":
                if not collecting and agents:
                    self.groups.append((agents, rules, delay))
                    agents, rules, delay = [], [], None
                agents.append(value.lower())
                collecting = True
                continue
            collecting = False
            if field in ("allow", "disallow") and value:
                rules.append((field == "allow", value))
            elif field == "crawl-delay":
                with contextlib.suppress(ValueError):
                    delay = float(value)
            elif field == "sitemap" and value:
                self.sitemaps.append(value)
        if agents:
            self.groups.append((agents, rules, delay))

    def group(self, agent):
        """The rules for the most specific matching user-agent group (or '*')."""
        agent, best, best_len = agent.lower(), None, -1
        for names, rules, delay in self.groups:
            for name in names:
                if name == "*" and best_len < 0:
                    best, best_len = (rules, delay), 0
                elif name != "*" and name in agent and len(name) > best_len:
                    best, best_len = (rules, delay), len(name)
        return best or ([], None)

    def can_fetch(self, agent, url):
        parts = urlsplit(url)
        target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        best_len, allowed = -1, True
        for allow, pattern in self.group(agent)[0]:
            regex = re.escape(pattern).replace(r"\*", ".*")
            if regex.endswith(r"\$"):
                regex = regex[:-2] + "$"
            if re.match(regex, target) and (len(pattern) > best_len or (
                    len(pattern) == best_len and allow)):
                best_len, allowed = len(pattern), allow
        return allowed

    def crawl_delay(self, agent):
        return self.group(agent)[1]

    def site_maps(self):
        return self.sitemaps


def load_robots(text):
    return Robots(text)


def page_title(html):
    match = TITLE.search(html)
    return " ".join(match.group(1).split())[:70] if match else ""


def crawl(urls, delay, fetch, sleep=time.sleep, out=print):
    """Visit each URL once, waiting `delay` seconds between requests."""
    results = []
    for number, url in enumerate(urls):
        if number:
            sleep(delay)
        results.append(fetch(url))
        out(results[-1]["line"])
    return results


def fetch_page(url, timeout=15):
    started = time.perf_counter()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            html = response.read(2_000_000).decode("utf-8", errors="replace")
            status, error = response.status, ""
    except urllib.error.HTTPError as err:
        status, html, error = err.code, "", f"HTTP {err.code}"
    except (urllib.error.URLError, OSError, ValueError) as err:
        status, html, error = 0, "", str(getattr(err, "reason", err))
    ms = round((time.perf_counter() - started) * 1000)
    line = (f"  {status or '---':>3} {ms:>5} ms {len(html):>7} B  {url}  "
            + (error or page_title(html)))
    return {"url": url, "status": status, "ms": ms, "line": line}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Explore a sitemap within robots.txt rules.")
    parser.add_argument("--sitemap", required=True, help="sitemap URL or file")
    parser.add_argument("--robots", help="robots.txt URL or file (default: the site's own)")
    parser.add_argument("--agent", default="*", help="robot name to check the rules for (*)")
    parser.add_argument("--follow-index", action="store_true",
                        help="fetch the sitemaps listed by a sitemap index (needs the network)")
    parser.add_argument("--limit", type=int, default=0, help="only the first N URLs")
    parser.add_argument("--fetch", action="store_true",
                        help="visit the allowed URLs (default only lists them)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="seconds between page requests (a larger robots Crawl-delay wins)")
    args = parser.parse_args(argv)

    try:
        kind, items = parse_sitemap(read_source(args.sitemap))
        if kind == "index":
            print(f"Sitemap index with {len(items)} sitemap(s):")
            for loc in items:
                print(f"  {loc}")
            if not args.follow_index:
                print("\nUse --follow-index to read them (this makes one request per sitemap).")
                return 0
            pages = []
            for loc in items:
                pages += parse_sitemap(read_source(loc))[1]
            items = pages
    except (OSError, ValueError, ET.ParseError, urllib.error.URLError) as err:
        print(f"Can't read the sitemap: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    robots_source = args.robots
    if not robots_source and "://" in args.sitemap:
        site = urlsplit(args.sitemap)
        robots_source = f"{site.scheme}://{site.netloc}/robots.txt"
    rules = None
    if robots_source:
        try:
            rules = load_robots(read_source(robots_source))
        except (OSError, urllib.error.URLError) as err:
            print(f"Note: couldn't read robots.txt ({getattr(err, 'reason', err)}); "
                  "assuming everything is allowed.", file=sys.stderr)
    host = urlsplit(items[0][0]).netloc if items else ""
    if args.limit:
        items = items[:args.limit]
    allowed, blocked, other_hosts = [], [], 0
    print(f"{len(items)} URL(s) in the sitemap" + (f", robots rules for '{args.agent}'"
                                                   if rules else ", no robots.txt checked"))
    for url, lastmod in items:
        if urlsplit(url).netloc != host:
            other_hosts += 1
            print(f"  OTHER SITE  {url}")
        elif rules and not rules.can_fetch(args.agent, url):
            blocked.append(url)
            print(f"  BLOCKED     {url}")
        else:
            allowed.append(url)
            print(f"  allowed     {url}" + (f"  (modified {lastmod})" if lastmod else ""))
    delay = max(args.delay, float(rules.crawl_delay(args.agent) or 0)) if rules else args.delay
    print(f"\n{len(allowed)} allowed, {len(blocked)} blocked by robots.txt"
          + (f", {other_hosts} on other sites (skipped)" if other_hosts else "") + ".")
    if rules and rules.crawl_delay(args.agent):
        print(f"robots.txt asks for a Crawl-delay of {rules.crawl_delay(args.agent)}s; "
              f"using {delay:g}s between requests.")
    if rules and rules.site_maps():
        print("Sitemaps declared in robots.txt: " + ", ".join(rules.site_maps()))
    if not args.fetch:
        print("Use --fetch to visit the allowed pages (one at a time, politely).")
        return 0
    print(f"\nVisiting {len(allowed)} page(s), {delay:g}s apart:")
    results = crawl(allowed, delay, fetch_page)
    bad = sum(not 200 <= r["status"] < 400 for r in results)
    print(f"\n{len(results) - bad} fetched, {bad} failed.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
