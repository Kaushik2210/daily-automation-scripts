"""Build a link graph of a small site (from a folder of HTML files, or by crawling a URL)."""
import argparse
import json
import posixpath
import sys
import time
import urllib.error  # web-ok: the network is only used with --url --fetch; --dir works offline
import urllib.request
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit

USER_AGENT = "daily-automation-scripts/1.0 (link graph builder)"
SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "sms:")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.title, self._in_title = [], "", False

    def handle_starttag(self, tag, attrs):
        if tag == "a" and dict(attrs).get("href"):
            self.hrefs.append(dict(attrs)["href"].strip())
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def parse_page(html):
    parser = Links()
    parser.feed(html)
    return " ".join(parser.title.split()), parser.hrefs


def local_resolver(pages_on_disk, assets):
    """Resolve a link found on page `page` to ('page', key), ('asset', None), ('external', host),
    ('broken', None) or ('ignore', None)."""
    def resolve(page, href):
        if not href or href.startswith(("#", *SKIP_SCHEMES)):
            return "ignore", None
        parts = urlsplit(href)
        if parts.scheme in ("http", "https") or href.startswith("//"):
            return "external", parts.netloc.lower()
        path = parts.path
        if not path:
            return "ignore", None
        target = posixpath.normpath(posixpath.join(posixpath.dirname(page), path.lstrip("/")
                                                   if path.startswith("/") else path))
        if path.endswith("/"):
            target = posixpath.join(target, "index.html")
        if target.startswith(".."):
            return "broken", None
        if target in pages_on_disk:
            return "page", target
        if target in assets:
            return "asset", None
        if posixpath.join(target, "index.html") in pages_on_disk:
            return "page", posixpath.join(target, "index.html")
        return "broken", None
    return resolve


def url_resolver(host):
    def resolve(page, href):
        if not href or href.startswith(("#", *SKIP_SCHEMES)):
            return "ignore", None
        absolute, _ = urldefrag(urljoin(page, href))
        parts = urlsplit(absolute)
        if parts.scheme not in ("http", "https"):
            return "ignore", None
        if parts.netloc.lower() != host:
            return "external", parts.netloc.lower()
        return "page", absolute
    return resolve


def build_graph(start, get_html, resolve, max_pages=200):
    """Walk the site from `start`. get_html(key) returns the HTML or None (a broken page)."""
    nodes, queue, seen = {}, deque([start]), {start}
    while queue and len(nodes) < max_pages:
        key = queue.popleft()
        html = get_html(key)
        node = {"title": "", "out": [], "external": [], "broken": [], "missing": html is None}
        nodes[key] = node
        if html is None:
            continue
        node["title"], hrefs = parse_page(html)
        for href in hrefs:
            kind, target = resolve(key, href)
            if kind == "page":
                if target not in node["out"] and target != key:
                    node["out"].append(target)
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
            elif kind == "external" and target not in node["external"]:
                node["external"].append(target)
            elif kind == "broken":
                node["broken"].append(href)
    return nodes


def analyse(nodes, start):
    """Return facts about the graph: inbound counts, orphans, dead ends, depths, broken links."""
    inbound = dict.fromkeys(nodes, 0)
    for node in nodes.values():
        for target in node["out"]:
            if target in inbound:
                inbound[target] += 1
    real = {k: v for k, v in nodes.items() if not v["missing"]}
    broken = [(k, h) for k, v in real.items() for h in v["broken"]]
    broken += [(k, t) for k, v in real.items() for t in v["out"] if nodes.get(t, {}).get("missing")]
    return {"inbound": inbound, "dead_ends": [k for k, v in real.items() if not v["out"]],
            "broken": broken}


def levels(nodes, start):
    """Breadth-first click distance from the start page."""
    depth, queue = {start: 0}, deque([start])
    while queue:
        current = queue.popleft()
        for target in nodes.get(current, {"out": []})["out"]:
            if target in nodes and target not in depth:
                depth[target] = depth[current] + 1
                queue.append(target)
    return depth


def to_dot(nodes):
    lines = ["digraph site {", "  rankdir=LR;", "  node [shape=box, fontsize=10];"]
    for key, node in nodes.items():
        label = (node["title"] or key).replace('"', "'")
        style = ", color=red" if node["missing"] else ""
        lines.append(f'  "{key}" [label="{label}"{style}];')
        lines += [f'  "{key}" -> "{target}";' for target in node["out"]]
    return "\n".join(lines + ["}"]) + "\n"


def local_site(directory):
    pages = {p.relative_to(directory).as_posix(): p for p in directory.rglob("*")
             if p.suffix.lower() in (".html", ".htm") and p.is_file()}
    assets = {p.relative_to(directory).as_posix() for p in directory.rglob("*")
              if p.is_file() and p.relative_to(directory).as_posix() not in pages}
    return pages, assets


def fetch_html(url, timeout=15):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if "html" not in response.headers.get("Content-Type", "html"):
                return ""
            return response.read(2_000_000).decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError):
        return None


def write_new(path, text):
    if path.exists():
        raise FileExistsError(f"{path} already exists; choose another name")
    path.write_text(text, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a link graph of a small site.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dir", type=Path, help="folder holding the site's HTML files")
    source.add_argument("--url", help="start page of a live site (needs --fetch)")
    parser.add_argument("--start", help="start page inside --dir (default: index.html)")
    parser.add_argument("--fetch", action="store_true", help="allow requests to the live site")
    parser.add_argument("--max-pages", type=int, default=50, help="most pages to visit (50)")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between requests (1)")
    parser.add_argument("--dot", type=Path, help="write a Graphviz .dot file (new file)")
    parser.add_argument("--json", type=Path, help="write the graph as JSON (new file)")
    args = parser.parse_args(argv)

    if args.dir:
        if not args.dir.is_dir():
            parser.error(f"not a folder: {args.dir}")
        pages, assets = local_site(args.dir)
        if not pages:
            print("No .html files found.", file=sys.stderr)
            return 1
        start = args.start or ("index.html" if "index.html" in pages else min(pages))
        if start not in pages:
            parser.error(f"start page not found: {start}")

        def get_html(key):
            if key not in pages:
                return None
            return pages[key].read_text(encoding="utf-8", errors="replace")
        resolve = local_resolver(set(pages), assets)
    else:
        if not args.fetch:
            print(f"Plan: would crawl {args.url} (same site only, up to {args.max_pages} pages, "
                  f"{args.delay:g}s apart). Add --fetch to do it.")
            return 0
        start, host, last = args.url, urlsplit(args.url).netloc.lower(), [0.0]
        resolve = url_resolver(host)

        def get_html(key):
            wait = last[0] + args.delay - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            last[0] = time.monotonic()
            return fetch_html(key)

    nodes = build_graph(start, get_html, resolve, args.max_pages)
    facts = analyse(nodes, start)
    depth = levels(nodes, start)
    real = {k: v for k, v in nodes.items() if not v["missing"]}
    links = sum(len(v["out"]) for v in real.values())
    external = sorted({h for v in real.values() for h in v["external"]})
    print(f"{len(real)} page(s), {links} internal link(s), {len(external)} external site(s); "
          f"start: {start}\n")
    print("Most linked-to pages:")
    for key, count in sorted(facts["inbound"].items(), key=lambda i: (-i[1], i[0]))[:5]:
        print(f"  {count:>2} in  {key}  {nodes[key]['title']}")
    print("\nClicks from the start page:")
    for key, level in sorted(depth.items(), key=lambda i: (i[1], i[0])):
        print(f"  {'  ' * level}{level}: {key}")
    orphans = sorted(set(pages) - set(depth)) if args.dir else []
    if orphans:
        print("\nNot reachable by clicking from the start page (orphans):")
        print("\n".join(f"  {o}" for o in orphans))
    if facts["dead_ends"]:
        print("\nDead ends (no links out): " + ", ".join(sorted(facts["dead_ends"])))
    if facts["broken"]:
        print("\nBroken internal links:")
        print("\n".join(f"  {page}  ->  {target}" for page, target in facts["broken"]))
    if external:
        print("\nExternal sites linked: " + ", ".join(external))
    try:
        if args.dot:
            write_new(args.dot, to_dot(nodes))
        if args.json:
            write_new(args.json, json.dumps({"start": start, "pages": nodes}, indent=1) + "\n")
    except FileExistsError as err:
        print(err, file=sys.stderr)
        return 1
    return 1 if facts["broken"] or orphans else 0


if __name__ == "__main__":
    sys.exit(main())
