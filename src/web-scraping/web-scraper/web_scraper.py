"""Scrape text or attributes from a page using CSS selectors, honoring robots.txt."""
import argparse
import csv
import io
import itertools
import json
import re
import sys
import urllib.error  # web-ok: the network is only used when you give a URL
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

AGENT = "daily-automation-scripts"
USER_AGENT = f"{AGENT}/1.0 (web scraper)"
MAX_BYTES = 2 * 1024 * 1024
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source",
        "track", "wbr"}
SKIP_TEXT = {"script", "style", "template", "noscript"}
PART = re.compile(r"#([\w-]+)|\.([\w-]+)|\[([\w:-]+)(?:([~^$*|]?=)[\"']?([^\]\"']*)[\"']?)?\]")


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.children = tag, attrs, parent, []

    def text(self):
        parts = []
        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag not in SKIP_TEXT:
                parts.append(child.text())
        return " ".join("".join(parts).split())

    def walk(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child.walk()


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = self.cur = Node("[document]", {}, None)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: v or "" for k, v in attrs}, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, {k: v or "" for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        node = self.cur
        while node.parent is not None and node.tag != tag:
            node = node.parent
        if node.tag == tag and node.parent is not None:
            self.cur = node.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse_html(html):
    builder = TreeBuilder()
    builder.feed(html)
    return builder.root


def parse_compound(text):
    tag = re.match(r"[\w*-]+", text)
    compound = {"tag": tag.group(0).lower() if tag else "*", "id": None, "classes": [],
                "attrs": []}
    for ident, klass, name, op, value in PART.findall(text):
        if ident:
            compound["id"] = ident
        elif klass:
            compound["classes"].append(klass)
        else:
            compound["attrs"].append((name, op, value))
    return compound


def parse_selector(selector):
    """Return a list of chains; a chain is [(combinator, compound), ...]."""
    chains = []
    for group in selector.split(","):
        tokens = re.findall(r">|[^\s>]+", group)
        if not tokens or tokens[0] == ">" or tokens[-1] == ">":
            raise ValueError(f"can't read selector: {selector!r}")
        chain, comb = [], " "
        for token in tokens:
            if token == ">":
                comb = ">"
            else:
                chain.append((comb, parse_compound(token)))
                comb = " "
        chains.append(chain)
    return chains


def attr_matches(node, name, op, value):
    if name not in node.attrs:
        return False
    have = node.attrs[name]
    return {"": True, "=": have == value, "^=": have.startswith(value),
            "$=": have.endswith(value), "*=": value in have,
            "~=": value in have.split(), "|=": have == value or have.startswith(value + "-")}[op]


def matches(node, c):
    if c["tag"] != "*" and node.tag != c["tag"]:
        return False
    if c["id"] and node.attrs.get("id") != c["id"]:
        return False
    classes = node.attrs.get("class", "").split()
    if any(k not in classes for k in c["classes"]):
        return False
    return all(attr_matches(node, *a) for a in c["attrs"])


def chain_matches(node, chain, i):
    if not matches(node, chain[i][1]):
        return False
    if i == 0:
        return True
    parent = node.parent
    if chain[i][0] == ">":
        return parent is not None and chain_matches(parent, chain, i - 1)
    while parent is not None:
        if chain_matches(parent, chain, i - 1):
            return True
        parent = parent.parent
    return False


def select(root, selector):
    chains = parse_selector(selector)
    return [n for n in root.walk() if any(chain_matches(n, ch, len(ch) - 1) for ch in chains)]


def extract(root, selector, attr=None, base=""):
    values = []
    for node in select(root, selector):
        value = node.attrs.get(attr, "") if attr else node.text()
        if attr in ("href", "src") and value and base:
            value = urljoin(base, value)
        if value:
            values.append(value)
    return values


def robots_allows(url, robots_text):
    parser = RobotFileParser()
    parser.parse(robots_text.splitlines())
    return parser.can_fetch(AGENT, url)


def fetch(url, timeout=15):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(MAX_BYTES).decode(charset, errors="replace")


def fetch_robots(url):
    parts = urlsplit(url)
    try:
        return fetch(f"{parts.scheme}://{parts.netloc}/robots.txt")
    except urllib.error.HTTPError as err:
        if 400 <= err.code < 500:
            return ""  # no robots.txt means everything is allowed
        raise


def render(results, fmt):
    if fmt == "json":
        return json.dumps(results, indent=2, ensure_ascii=False)
    if fmt == "csv":
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(results)
        writer.writerows(itertools.zip_longest(*results.values(), fillvalue=""))
        return out.getvalue().rstrip("\n")
    return "\n".join(f"[{label}] {value}" for label, values in results.items() for value in values)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scrape a page with CSS selectors.")
    parser.add_argument("source", help="a page URL, or a saved .html file")
    parser.add_argument("-s", "--selector", action="append", required=True, metavar="[NAME=]CSS",
                        help="what to scrape; repeat for several, e.g. title=h1 or 'a.buy'")
    parser.add_argument("--attr", help="read this attribute (href, src...) instead of the text")
    parser.add_argument("--format", choices=["text", "json", "csv"], default="text")
    parser.add_argument("--limit", type=int, default=0, help="max values per selector (0 = all)")
    parser.add_argument("--base", default="", help="page address, to resolve relative links")
    parser.add_argument("--robots-file", type=Path, help="robots.txt to check a URL against")
    args = parser.parse_args(argv)

    path, base = Path(args.source), args.base
    try:
        if "://" in args.source:
            robots = (args.robots_file.read_text(encoding="utf-8", errors="replace")
                      if args.robots_file else fetch_robots(args.source))
            if not robots_allows(args.source, robots):
                print(f"robots.txt asks bots not to fetch {args.source} - skipping it.")
                return 2
            html, base = fetch(args.source), base or args.source
        elif path.is_file():
            html = path.read_text(encoding="utf-8", errors="replace")
        else:
            parser.error(f"not a URL or a file: {args.source}")
        root, results = parse_html(html), {}
        for index, spec in enumerate(args.selector, 1):
            label, _, css = spec.partition("=")
            if not css or any(ch in label for ch in " .#[>"):
                label, css = f"selector{index}", spec
            values = extract(root, css, args.attr, base)
            results[label] = values[:args.limit] if args.limit > 0 else values
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't scrape {args.source}: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    print(render(results, args.format))
    return 0 if any(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
