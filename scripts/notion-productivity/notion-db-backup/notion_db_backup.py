"""Back up a Notion database to a JSON file (read-only: nothing in Notion is changed)."""
import argparse
import json
import os
import re
import sys
import urllib.error  # web-ok: the network is only used when you give a database id
import urllib.request
from datetime import datetime
from pathlib import Path

API = os.environ.get("NOTION_API_URL", "https://api.notion.com/v1").rstrip("/")
VERSION = "2022-06-28"


def notion(method, path, body=None):
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise ValueError("set the NOTION_TOKEN environment variable to your integration token")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(f"{API}{path}", data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Notion-Version": VERSION,
        "Content-Type": "application/json", "User-Agent": "daily-automation-scripts/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def fetch_all(database_id):
    """Return (database object, every page in it). Query paging is followed to the end."""
    database = notion("GET", f"/databases/{database_id}")
    pages, cursor = [], None
    while True:
        data = notion("POST", f"/databases/{database_id}/query",
                      {"page_size": 100, **({"start_cursor": cursor} if cursor else {})})
        pages += data.get("results", [])
        cursor = data.get("next_cursor")
        if not data.get("has_more") or not cursor:
            return database, pages


def plain(parts):
    return "".join(p.get("plain_text", "") for p in parts or [])


def simple_value(prop):
    """A Notion property as an ordinary Python value (text, list, number, bool)."""
    kind = prop.get("type")
    value = prop.get(kind)
    if kind in ("title", "rich_text"):
        return plain(value)
    if kind in ("select", "status"):
        return (value or {}).get("name")
    if kind == "multi_select":
        return [item["name"] for item in value or []]
    if kind == "date":
        if not value:
            return None
        return value["start"] + (f" -> {value['end']}" if value.get("end") else "")
    if kind == "people":
        return [person.get("name") or person.get("id") for person in value or []]
    if kind == "files":
        return [item.get("name") for item in value or []]
    if kind == "relation":
        return [item["id"] for item in value or []]
    if kind == "formula":
        inner = (value or {}).get("type")
        if inner == "date":
            return simple_value({"type": "date", "date": value.get("date")})
        return (value or {}).get(inner)  # string, number or boolean results
    if kind == "unique_id":
        return f"{value.get('prefix') or ''}{value.get('number')}"
    if kind in ("checkbox", "number", "url", "email", "phone_number", "created_time",
                "last_edited_time"):
        return value
    return None


def simplify(pages):
    return [{"id": page.get("id"), "url": page.get("url"), "created": page.get("created_time"),
             "edited": page.get("last_edited_time"),
             "properties": {name: simple_value(prop)
                            for name, prop in page.get("properties", {}).items()}}
            for page in pages]


def default_name(database_id, today):
    short = re.sub(r"[^0-9a-zA-Z]", "", database_id)[:8] or "db"
    return f"notion-backup-{short}-{today:%Y%m%d}.json"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Back up a Notion database to JSON.")
    parser.add_argument("database", nargs="?", help="Notion database id")
    parser.add_argument("--from-file", type=Path, help="convert a saved database query instead")
    parser.add_argument("--format", choices=["raw", "simple"], default="raw",
                        help="raw = all Notion returns (best for backups); simple = tidy rows")
    parser.add_argument("--out", type=Path, help="new file to write (default: a dated name)")
    parser.add_argument("--stdout", action="store_true", help="print the JSON instead of saving")
    args = parser.parse_args(argv)
    if not (args.database or args.from_file):
        parser.error("give a database id or --from-file FILE")

    try:
        if args.from_file:
            pages = json.loads(args.from_file.read_text(encoding="utf-8"))["results"]
            database, label = None, args.from_file.stem
        else:
            database, pages = fetch_all(args.database)
            label = args.database
    except urllib.error.HTTPError as err:
        hint = {401: "bad token", 404: "database not found - share it with your integration",
                429: "rate limited, try again shortly"}
        print(f"Notion said {err.code} ({hint.get(err.code, err.reason)}).", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError) as err:
        print(f"Couldn't read the database: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    backup = {"exported_at": datetime.now().isoformat(timespec="seconds"), "database_id": label,
              "page_count": len(pages)}
    if args.format == "raw":
        backup.update({"database": database, "pages": pages})
    else:
        backup["rows"] = simplify(pages)
    text = json.dumps(backup, indent=2, ensure_ascii=False) + "\n"
    if args.stdout:
        print(text, end="")
        return 0
    target = args.out or Path(default_name(label, datetime.now()))
    if target.exists():
        print(f"{target} already exists - pick a new name so nothing is overwritten.")
        return 1
    target.write_text(text, encoding="utf-8")
    names = sorted({name for page in pages for name in page.get("properties", {})})
    print(f"Saved {len(pages)} page(s) to {target} ({len(text.encode('utf-8')) / 1024:.1f} KB).")
    print(f"Properties: {', '.join(names) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
