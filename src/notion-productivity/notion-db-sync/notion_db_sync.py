"""Sync a CSV file into a Notion database: add new rows, update changed ones. Dry run by default."""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error  # web-ok: the network is only used when you give a database id
import urllib.request
from pathlib import Path

API = os.environ.get("NOTION_API_URL", "https://api.notion.com/v1").rstrip("/")
VERSION = "2022-06-28"
TRUE_WORDS = {"true", "yes", "y", "1", "x", "done", "checked"}
SIMPLE = {"url", "email", "phone_number"}
SUPPORTED = {"title", "rich_text", "select", "status", "multi_select", "date", "checkbox",
             "number"} | SIMPLE


def notion(method, path, body=None):
    """Call the Notion API. The token comes from the NOTION_TOKEN environment variable."""
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise ValueError("set the NOTION_TOKEN environment variable to your integration token")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(f"{API}{path}", data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Notion-Version": VERSION,
        "Content-Type": "application/json", "User-Agent": "daily-automation-scripts/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def plain(rich):
    return "".join(part.get("plain_text", "") for part in rich or [])


def prop_value(prop):
    """A Notion property as a plain, comparable string."""
    kind = prop.get("type")
    value = prop.get(kind)
    if kind in ("title", "rich_text"):
        return plain(value)
    if kind in ("select", "status"):
        return (value or {}).get("name", "")
    if kind == "multi_select":
        return ";".join(sorted(item["name"] for item in value or []))
    if kind == "date":
        return (value or {}).get("start", "") or ""
    if kind == "checkbox":
        return "true" if value else "false"
    if kind == "number":
        return "" if value is None else f"{value:g}"
    if kind in SIMPLE:
        return value or ""
    return ""


def normalise(kind, text):
    """A CSV cell in the same canonical form as prop_value."""
    text = (text or "").strip()
    if kind == "checkbox":
        return "true" if text.lower() in TRUE_WORDS else "false"
    if kind == "number":
        try:
            return f"{float(text):g}" if text else ""
        except ValueError:
            return text
    if kind == "multi_select":
        return ";".join(sorted({p.strip() for p in re.split(r"[;,]", text) if p.strip()}))
    return text


def to_property(kind, text):
    """The JSON Notion expects when writing a property of this type."""
    text = normalise(kind, text)
    if kind == "title":
        return {"title": [{"text": {"content": text}}]}
    if kind == "rich_text":
        return {"rich_text": [{"text": {"content": text}}] if text else []}
    if kind in ("select", "status"):
        return {kind: {"name": text} if text else None}
    if kind == "multi_select":
        return {"multi_select": [{"name": n} for n in text.split(";") if n]}
    if kind == "date":
        return {"date": {"start": text} if text else None}
    if kind == "checkbox":
        return {"checkbox": text == "true"}
    if kind == "number":
        return {"number": float(text) if text else None}
    return {kind: text or None}


def column_types(pages, schema=None):
    types = {name: prop["type"] for name, prop in (schema or {}).items()}
    for page in pages:
        for name, prop in page.get("properties", {}).items():
            types.setdefault(name, prop.get("type"))
    return types


def title_column(types):
    return next((name for name, kind in types.items() if kind == "title"), None)


def make_plan(rows, pages, types, key):
    """Return (creates, updates, untouched count, skipped column names)."""
    skipped = sorted({c for row in rows for c in row if types.get(c) not in SUPPORTED})
    by_key = {prop_value(p["properties"][key]).casefold(): p
              for p in pages if key in p["properties"]}
    creates, updates, seen = [], [], set()
    for row in rows:
        name = (row.get(key) or "").strip()
        if not name:
            continue
        seen.add(name.casefold())
        usable = {c: v for c, v in row.items() if c not in skipped}
        page = by_key.get(name.casefold())
        if page is None:
            creates.append({c: to_property(types[c], v) for c, v in usable.items()})
            continue
        changed = {c: v for c, v in usable.items() if c != key and c in page["properties"]
                   and normalise(types[c], v) != prop_value(page["properties"][c])}
        if changed:
            payload = {c: to_property(types[c], v) for c, v in changed.items()}
            updates.append((page["id"], name, payload, sorted(changed)))
    return creates, updates, len([k for k in by_key if k not in seen]), skipped


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [{(k or "").strip(): (v or "") for k, v in row.items()}
                for row in csv.DictReader(handle)]


def fetch_database(database_id):
    schema = notion("GET", f"/databases/{database_id}").get("properties", {})
    pages, cursor = [], None
    while True:
        data = notion("POST", f"/databases/{database_id}/query",
                      {"page_size": 100, **({"start_cursor": cursor} if cursor else {})})
        pages += data.get("results", [])
        cursor = data.get("next_cursor")
        if not data.get("has_more") or not cursor:
            return schema, pages


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sync a CSV into a Notion database.")
    parser.add_argument("csv", type=Path, help="the CSV file (first row = column names)")
    parser.add_argument("--db", help="Notion database id (or set it via --existing for a plan)")
    parser.add_argument("--existing", type=Path,
                        help="saved database query (JSON) instead of Notion")
    parser.add_argument("--key", help="column that identifies a row (default: the title column)")
    parser.add_argument("--delay", type=float, default=0.35, help="seconds between writes (0.35)")
    parser.add_argument("--apply", action="store_true", help="actually change the database")
    args = parser.parse_args(argv)
    if not (args.db or args.existing):
        parser.error("give --db DATABASE_ID or --existing FILE")
    if args.apply and not args.db:
        parser.error("--apply needs --db so there is a database to change")
    if not args.csv.is_file():
        parser.error(f"not a file: {args.csv}")

    try:
        rows = read_csv(args.csv)
        if args.existing:
            schema, pages = None, json.loads(args.existing.read_text(encoding="utf-8"))["results"]
        else:
            schema, pages = fetch_database(args.db)
    except urllib.error.HTTPError as err:
        hint = {401: "bad token", 404: "database not found - share it with your integration",
                429: "rate limited, try again shortly"}
        print(f"Notion said {err.code} ({hint.get(err.code, err.reason)}).", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError, KeyError) as err:
        print(f"Couldn't read the data: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    if not rows:
        print("The CSV has no rows.")
        return 1

    types = column_types(pages, schema)
    key = args.key or title_column(types)
    if not key or key not in rows[0]:
        print(f"The CSV needs a '{key or 'title'}' column to match rows on.", file=sys.stderr)
        return 1
    creates, updates, untouched, skipped = make_plan(rows, pages, types, key)

    print(f"{len(creates)} to add, {len(updates)} to update, {untouched} in Notion not in the CSV "
          "(left alone).")
    if skipped:
        print(f"Skipping columns Notion can't take from a CSV: {', '.join(skipped)}")
    for props in creates:
        print(f"  + {props[key]['title'][0]['text']['content']}")
    for _page_id, name, _props, fields in updates:
        print(f"  ~ {name}: {', '.join(fields)}")
    if not args.apply:
        print("\nDry run - nothing changed. Add --apply to write these changes to Notion.")
        return 0

    try:
        for props in creates:
            notion("POST", "/pages", {"parent": {"database_id": args.db}, "properties": props})
            time.sleep(args.delay)
        for page_id, _name, props, _fields in updates:
            notion("PATCH", f"/pages/{page_id}", {"properties": props})
            time.sleep(args.delay)
    except urllib.error.HTTPError as err:
        print(f"Notion said {err.code} while writing; some changes may have been made.",
              file=sys.stderr)
        return 1
    print(f"\nDone: {len(creates)} added, {len(updates)} updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
