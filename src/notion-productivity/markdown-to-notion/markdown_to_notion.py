"""Turn a markdown file into Notion blocks and append them to a page. Dry run by default."""
import argparse
import json
import os
import re
import sys
import time
import urllib.error  # web-ok: the network is only used with --apply
import urllib.request
from collections import Counter
from pathlib import Path

API = os.environ.get("NOTION_API_URL", "https://api.notion.com/v1").rstrip("/")
VERSION = "2022-06-28"
MAX_TEXT = 2000   # Notion rejects rich text longer than this
BATCH = 100       # Notion accepts at most 100 blocks per request
LANGUAGES = {"py": "python", "js": "javascript", "ts": "typescript", "sh": "shell", "bash": "bash",
             "zsh": "shell", "yml": "yaml", "md": "markdown", "": "plain text",
             "text": "plain text"}
KNOWN = {"python", "javascript", "typescript", "bash", "shell", "json", "yaml", "html", "css",
         "sql", "markdown", "go", "rust", "java", "c", "c++", "c#", "ruby", "php", "plain text",
         "diff"}
INLINE = re.compile(r"\*\*(?P<bold>.+?)\*\*|~~(?P<strike>.+?)~~|`(?P<code>[^`]+)`"
                    r"|\[(?P<label>[^\]]+)\]\((?P<url>[^)\s]+)\)|\*(?P<ital>[^*\s][^*]*?)\*"
                    r"|(?<!\w)_(?P<ital2>[^_]+)_(?!\w)")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET = re.compile(r"^(\s*)[-*+]\s+(?:\[(?P<box>[ xX])\]\s+)?(.*)$")
NUMBERED = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
IMAGE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<url>https?://[^)\s]+)\)\s*$")


def rich_part(text, url=None, **annotations):
    part = {"type": "text", "text": {"content": text}}
    if url:
        part["text"]["link"] = {"url": url}
    if annotations:
        part["annotations"] = {k: True for k in annotations}
    return part


def inline(text):
    """Markdown inline formatting -> a list of Notion rich_text parts (each <= 2000 chars)."""
    parts, position = [], 0
    for match in INLINE.finditer(text):
        if match.start() > position:
            parts.append(rich_part(text[position:match.start()]))
        if match.group("bold"):
            parts.append(rich_part(match.group("bold"), bold=True))
        elif match.group("strike"):
            parts.append(rich_part(match.group("strike"), strikethrough=True))
        elif match.group("code"):
            parts.append(rich_part(match.group("code"), code=True))
        elif match.group("label"):
            parts.append(rich_part(match.group("label"), url=match.group("url")))
        else:
            parts.append(rich_part(match.group("ital") or match.group("ital2"), italic=True))
        position = match.end()
    if position < len(text):
        parts.append(rich_part(text[position:]))
    chunks = []
    for part in parts:
        content = part["text"]["content"]
        for start in range(0, max(len(content), 1), MAX_TEXT):
            piece = json.loads(json.dumps(part))
            piece["text"]["content"] = content[start:start + MAX_TEXT]
            chunks.append(piece)
    return chunks


def block(kind, text="", **extra):
    return {"object": "block", "type": kind, kind: {"rich_text": inline(text), **extra}}


def convert(markdown):
    """Convert markdown text into a list of Notion block dicts (lists keep their nesting)."""
    blocks, paragraph, stack = [], [], []
    lines = markdown.replace("\t", "    ").splitlines()
    index = 0

    def flush():
        if paragraph:
            blocks.append(block("paragraph", " ".join(paragraph)))
            paragraph.clear()

    while index < len(lines):
        line = lines[index]
        index += 1
        fence = re.match(r"^```\s*(\S*)\s*$", line.strip())
        if fence:
            flush()
            stack.clear()
            code = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            index += 1
            language = LANGUAGES.get(fence.group(1).lower(), fence.group(1).lower())
            blocks.append({"object": "block", "type": "code", "code": {
                "rich_text": [rich_part(chunk) for chunk in _split("\n".join(code))],
                "language": language if language in KNOWN else "plain text"}})
            continue
        if not line.strip():
            flush()
            stack.clear()
            continue
        heading = HEADING.match(line)
        bullet, numbered = BULLET.match(line), NUMBERED.match(line)
        if re.fullmatch(r"\s*([-*_])(\s*\1){2,}\s*", line):
            flush()
            stack.clear()
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif heading:
            flush()
            stack.clear()
            blocks.append(block(f"heading_{min(len(heading.group(1)), 3)}", heading.group(2)))
        elif bullet or numbered:
            flush()
            match = bullet or numbered
            indent = len(match.group(1))
            if bullet and bullet.group("box"):
                item = block("to_do", bullet.group(3), checked=bullet.group("box").lower() == "x")
            elif bullet:
                item = block("bulleted_list_item", bullet.group(3))
            else:
                item = block("numbered_list_item", numbered.group(2))
            while stack and stack[-1][0] >= indent:
                stack.pop()
            if stack:
                parent = stack[-1][1]
                parent[parent["type"]].setdefault("children", []).append(item)
            else:
                blocks.append(item)
            stack.append((indent, item))
        elif line.lstrip().startswith(">"):
            flush()
            stack.clear()
            blocks.append(block("quote", line.lstrip()[1:].strip()))
        elif IMAGE.match(line.strip()):
            flush()
            stack.clear()
            image = IMAGE.match(line.strip())
            blocks.append({"object": "block", "type": "image", "image": {
                "type": "external", "external": {"url": image.group("url")},
                "caption": inline(image.group("alt")) if image.group("alt") else []}})
        else:
            stack.clear()
            paragraph.append(line.strip())
    flush()
    return blocks


def _split(text):
    return [text[i:i + MAX_TEXT] for i in range(0, max(len(text), 1), MAX_TEXT)]


def count_blocks(blocks):
    total = len(blocks)
    for item in blocks:
        total += count_blocks(item.get(item["type"], {}).get("children", []))
    return total


def append_blocks(page_id, blocks, delay):
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise ValueError("set the NOTION_TOKEN environment variable to your integration token")
    for start in range(0, len(blocks), BATCH):
        body = json.dumps({"children": blocks[start:start + BATCH]}).encode("utf-8")
        request = urllib.request.Request(
            f"{API}/blocks/{page_id}/children", data=body, method="PATCH",
            headers={"Authorization": f"Bearer {token}", "Notion-Version": VERSION,
                     "Content-Type": "application/json",
                     "User-Agent": "daily-automation-scripts/1.0"})
        with urllib.request.urlopen(request, timeout=30):
            pass
        time.sleep(delay)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Push a markdown file to a Notion page.")
    parser.add_argument("file", type=Path, help="the markdown file")
    parser.add_argument("--page", help="Notion page id or URL to append to")
    parser.add_argument("--json", action="store_true", help="print the Notion blocks as JSON")
    parser.add_argument("--delay", type=float, default=0.35, help="seconds between requests (0.35)")
    parser.add_argument("--apply", action="store_true", help="actually add the blocks to the page")
    args = parser.parse_args(argv)
    if args.apply and not args.page:
        parser.error("--apply needs --page PAGE_ID")
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")

    blocks = convert(args.file.read_text(encoding="utf-8-sig"))
    if not blocks:
        print("The file has no content to push.")
        return 1
    if args.json:
        print(json.dumps(blocks, indent=2, ensure_ascii=False))
        return 0
    kinds = Counter(item["type"] for item in blocks)
    print(f"{args.file.name}: {len(blocks)} top-level block(s), {count_blocks(blocks)} in all")
    print("  " + ", ".join(f"{n} {kind.replace('_', ' ')}" for kind, n in kinds.most_common()))
    if not args.apply:
        print("\nDry run - nothing sent. Add --page PAGE_ID --apply to append these to a page.")
        return 0
    match = re.search(r"([0-9a-fA-F]{32})(?:[?#]|$)", args.page.replace("-", ""))
    try:
        append_blocks(match.group(1) if match else args.page, blocks, args.delay)
    except urllib.error.HTTPError as err:
        hint = {400: "Notion rejected the content", 401: "bad token",
                404: "page not found - share it with your integration"}
        print(f"Notion said {err.code} ({hint.get(err.code, err.reason)}).", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't send: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    print(f"Appended {len(blocks)} block(s) to the page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
