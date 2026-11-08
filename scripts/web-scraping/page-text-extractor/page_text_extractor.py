"""Pull the readable article text out of a web page, without menus, ads and scripts."""
import argparse
import sys
import textwrap
import urllib.error  # web-ok: the network is only used when you give a URL
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

USER_AGENT = "daily-automation-scripts/1.0 (page text extractor)"
MAX_BYTES = 5 * 1024 * 1024
SKIPPED = {"script", "style", "noscript", "template", "svg", "nav", "footer", "aside", "form",
           "button", "select", "iframe"}
BREAKS = {"p", "div", "li", "ul", "ol", "br", "tr", "section", "article", "main", "table",
          "blockquote", "pre", "figcaption", "dd", "dt", "header", "h1", "h2", "h3", "h4", "h5",
          "h6"}
WORDS_PER_MINUTE = 220


class ArticleParser(HTMLParser):
    """Collect text blocks, remembering whether each sat inside <article> or <main>."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.blocks = "", []
        self._parts, self._kind, self._skip = [], "p", 0
        self._article = self._main = 0
        self._in_title = False

    def _flush(self):
        text = " ".join("".join(self._parts).split())
        if text and not self._in_title:
            self.blocks.append({"kind": self._kind, "text": text,
                                "article": self._article > 0, "main": self._main > 0})
        self._parts, self._kind = [], "p"

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag in SKIPPED or (tag == "header" and not self._article):
            self._skip += 1
        if tag in BREAKS:
            self._flush()
        if tag == "article":
            self._article += 1
        elif tag == "main":
            self._main += 1
        elif tag in ("li", "blockquote", "pre") or (tag[0] == "h" and tag[1:].isdigit()):
            self._kind = tag

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in BREAKS:
            self._flush()
        if tag in SKIPPED or (tag == "header" and self._skip and not self._article):
            self._skip = max(self._skip - 1, 0)
        if tag == "article":
            self._article = max(self._article - 1, 0)
        elif tag == "main":
            self._main = max(self._main - 1, 0)

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self._parts.append(data)


def extract(html):
    """Return (title, blocks) for the most article-like part of the page."""
    parser = ArticleParser()
    parser.feed(html)
    parser._flush()
    blocks = parser.blocks
    for region in ("article", "main"):
        chosen = [b for b in blocks if b[region]]
        if chosen:
            blocks = chosen
            break
    title = " ".join(parser.title.split()) or next(
        (b["text"] for b in blocks if b["kind"] == "h1"), "")
    return title, blocks


def render(blocks, width=80):
    lines = []
    for block in blocks:
        kind, text = block["kind"], block["text"]
        if kind[0] == "h" and kind[1:].isdigit():
            lines.append("#" * int(kind[1:]) + " " + text)
        elif kind == "li":
            lines.append(textwrap.fill(text, width, initial_indent="- ", subsequent_indent="  "))
        elif kind == "blockquote":
            lines.append(textwrap.fill(text, width, initial_indent="> ", subsequent_indent="> "))
        elif kind == "pre":
            lines.append(text)
        else:
            lines.append(textwrap.fill(text, width))
    return "\n\n".join(lines)


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
    parser = argparse.ArgumentParser(description="Extract the readable text from a page.")
    parser.add_argument("source", help="a page URL, or a saved .html file")
    parser.add_argument("--width", type=int, default=80, help="wrap lines at this width (80)")
    parser.add_argument("--out", type=Path, help="save the text to this new file")
    args = parser.parse_args(argv)
    if args.out and args.out.exists():
        print(f"{args.out} already exists - pick a new name so nothing is overwritten.")
        return 1
    try:
        title, blocks = extract(load(args.source))
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't load {args.source}: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    body = render(blocks, max(args.width, 20))
    if not body:
        print("No readable text found on that page.")
        return 1
    words = len(body.split())
    minutes = max(1, round(words / WORDS_PER_MINUTE))
    if args.out:
        args.out.write_text((f"# {title}\n\n" if title else "") + body + "\n", encoding="utf-8")
        print(f"Saved {words} words to {args.out}.")
        return 0
    print(f"{title}\n({words} words, about {minutes} min read)\n" if title else
          f"({words} words, about {minutes} min read)\n")
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
