"""Export Notion pages to markdown. Prints by default; --out-dir with --apply writes files."""
import argparse
import json
import os
import re
import sys
import urllib.error  # web-ok: the network is only used when you give a Notion page id
import urllib.request
from pathlib import Path

API = os.environ.get("NOTION_API_URL", "https://api.notion.com/v1").rstrip("/")
VERSION = "2022-06-28"
LIST_GROUPS = {"bulleted_list_item": "list", "to_do": "list", "toggle": "list",
               "numbered_list_item": "numbered"}


def notion_get(path):
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise ValueError("set the NOTION_TOKEN environment variable to your integration token")
    request = urllib.request.Request(f"{API}{path}", headers={
        "Authorization": f"Bearer {token}", "Notion-Version": VERSION,
        "User-Agent": "daily-automation-scripts/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def fetch_children(block_id):
    """All child blocks of a page or block, following Notion's paging."""
    blocks, cursor = [], None
    while True:
        query = "?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
        data = notion_get(f"/blocks/{block_id}/children{query}")
        blocks += data.get("results", [])
        cursor = data.get("next_cursor")
        if not data.get("has_more") or not cursor:
            return blocks


def page_title(page_id):
    page = notion_get(f"/pages/{page_id}")
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return "".join(t.get("plain_text", "") for t in prop["title"])
    return page_id


def rich(parts):
    """Notion rich text -> markdown with bold, italic, code, strikethrough and links."""
    out = []
    for part in parts or []:
        text = part.get("plain_text", "")
        if not text.strip():
            out.append(text)
            continue
        ann = part.get("annotations") or {}
        lead, core, trail = re.match(r"(\s*)(.*?)(\s*)$", text, re.DOTALL).groups()
        if ann.get("code"):
            core = f"`{core}`"
        if ann.get("bold"):
            core = f"**{core}**"
        if ann.get("italic"):
            core = f"*{core}*"
        if ann.get("strikethrough"):
            core = f"~~{core}~~"
        if part.get("href"):
            core = f"[{core}]({part['href']})"
        out.append(lead + core + trail)
    return "".join(out)


def media_url(data):
    return (data.get("external") or data.get("file") or {}).get("url", "")


def blocks_to_markdown(blocks, children=None, depth=0):
    """Convert Notion blocks to markdown lines. `children(block_id)` loads nested blocks."""
    lines, number, previous = [], 0, ""
    pad = "  " * depth
    for block in blocks:
        kind = block.get("type", "")
        data = block.get(kind) or {}
        number = number + 1 if kind == "numbered_list_item" else 0
        group = LIST_GROUPS.get(kind, kind)
        if lines and lines[-1] != "" and group != previous:
            lines.append("")  # blank line between a list and whatever comes next
        previous = group
        text = rich(data.get("rich_text"))
        if kind in ("heading_1", "heading_2", "heading_3"):
            lines += [f"{'#' * int(kind[-1])} {text}", ""]
        elif kind == "paragraph":
            lines += [pad + text, ""] if depth == 0 else [pad + text]
        elif kind == "bulleted_list_item":
            lines.append(f"{pad}- {text}")
        elif kind == "numbered_list_item":
            lines.append(f"{pad}{number}. {text}")
        elif kind == "to_do":
            lines.append(f"{pad}- [{'x' if data.get('checked') else ' '}] {text}")
        elif kind == "toggle":
            lines.append(f"{pad}- **{text}**")
        elif kind == "quote":
            lines += [f"> {text}", ""]
        elif kind == "callout":
            icon = (data.get("icon") or {}).get("emoji", "")
            lines += [f"> {icon} {text}".replace(">  ", "> ").rstrip(), ""]
        elif kind == "code":
            language = data.get("language", "").replace("plain text", "")
            lines += [f"```{language}", plain_text(data.get("rich_text")), "```", ""]
        elif kind == "divider":
            lines += ["---", ""]
        elif kind == "image":
            lines += [f"![{rich(data.get('caption'))}]({media_url(data)})", ""]
        elif kind in ("bookmark", "embed", "link_preview"):
            lines += [f"<{data.get('url', '')}>", ""]
        elif kind == "child_page":
            lines += [f"- Sub-page: {data.get('title', '')}"]
        elif kind == "table" and children and block.get("has_children"):
            lines += table_to_markdown(children(block["id"])) + [""]
            continue
        else:
            lines += [f"<!-- unsupported block: {kind} -->", ""]
        if children and block.get("has_children") and kind != "child_page":
            lines += blocks_to_markdown(children(block["id"]), children, depth + 1)
    return lines


def plain_text(parts):
    return "".join(p.get("plain_text", "") for p in parts or [])


def table_to_markdown(rows):
    cells = [[rich(cell) for cell in (row.get("table_row") or {}).get("cells", [])]
             for row in rows]
    if not cells:
        return []
    table = ["| " + " | ".join(cells[0]) + " |", "|" + " --- |" * len(cells[0])]
    return table + ["| " + " | ".join(row) + " |" for row in cells[1:]]


def to_markdown(title, blocks, children=None):
    body = "\n".join(blocks_to_markdown(blocks, children))
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return (f"# {title}\n\n" if title else "") + body + "\n"


def slugify(title):
    return re.sub(r"[^\w]+", "-", title.lower()).strip("-")[:60] or "page"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export Notion pages to markdown.")
    parser.add_argument("pages", nargs="*", help="Notion page ids (or full page URLs)")
    parser.add_argument("--from-file", type=Path,
                        help="a saved block list (JSON) instead of Notion")
    parser.add_argument("--title", default="", help="title to use with --from-file")
    parser.add_argument("--out-dir", type=Path, help="write one .md file per page here")
    parser.add_argument("--apply", action="store_true", help="actually write the files")
    args = parser.parse_args(argv)
    if not (args.pages or args.from_file):
        parser.error("give page ids or --from-file FILE")

    exports = []  # (title, markdown)
    try:
        if args.from_file:
            blocks = json.loads(args.from_file.read_text(encoding="utf-8"))["results"]
            exports.append((args.title, to_markdown(args.title, blocks)))
        for page in args.pages:
            match = re.search(r"([0-9a-fA-F]{32})(?:[?#]|$)", page.replace("-", ""))
            page_id = match.group(1) if match else page
            title = page_title(page_id)
            exports.append((title, to_markdown(title, fetch_children(page_id), fetch_children)))
    except urllib.error.HTTPError as err:
        hint = {401: "bad token", 404: "page not found - share it with your integration",
                429: "rate limited, try again shortly"}
        print(f"Notion said {err.code} ({hint.get(err.code, err.reason)}).", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError) as err:
        print(f"Couldn't export: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    if not args.out_dir:
        for _title, markdown in exports:
            print(markdown, end="" if len(exports) == 1 else "\n---\n\n")
        return 0
    for title, markdown in exports:
        target = args.out_dir / f"{slugify(title)}.md"
        if target.exists():
            print(f"skipped {target} (already exists)")
        elif not args.apply:
            print(f"would write {target} ({len(markdown.splitlines())} lines)")
        else:
            args.out_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(markdown, encoding="utf-8")
            print(f"wrote {target}")
    if not args.apply:
        print("Dry run - nothing written. Add --apply to create the files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
