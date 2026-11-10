"""Import tasks from a plain text file into a Notion database. Dry run by default."""
import argparse
import json
import os
import re
import sys
import time
import urllib.error  # web-ok: the network is only used when you give a database id
import urllib.request
from datetime import date, timedelta
from pathlib import Path

API = os.environ.get("NOTION_API_URL", "https://api.notion.com/v1").rstrip("/")
VERSION = "2022-06-28"
LINE = re.compile(r"^\s*(?:[-*+]\s*)?(?:\[(?P<box>[ xX])\]\s*)?(?P<text>.+?)\s*$")


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


def resolve_date(word, today):
    word = word.lower()
    if word == "today":
        return today
    if word == "tomorrow":
        return today + timedelta(days=1)
    plus = re.fullmatch(r"\+(\d{1,3})d", word)
    if plus:
        return today + timedelta(days=int(plus.group(1)))
    return date.fromisoformat(word)


def parse_tasks(text, today):
    """Return task dicts: title, done, due (ISO text or ''), tags, priority."""
    tasks = []
    for number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or re.match(r"^\s*#\s", raw) or raw.strip() == "#":
            continue
        match = LINE.match(raw)
        body = match.group("text")
        task = {"line": number, "done": (match.group("box") or " ").lower() == "x", "due": "",
                "tags": [], "priority": ""}
        for token in body.split():
            if token.startswith("@") and len(token) > 1:
                try:
                    task["due"] = resolve_date(token[1:], today).isoformat()
                except ValueError:
                    continue
            elif token.startswith("#") and len(token) > 1:
                task["tags"].append(token[1:])
            elif re.fullmatch(r"!(high|medium|low)", token.lower()):
                task["priority"] = token[1:].lower()
            else:
                continue
            body = body.replace(token, "", 1)
        task["title"] = " ".join(body.split())
        if task["title"] and not re.fullmatch(r"\[[ xX]?\]", task["title"]):
            tasks.append(task)
    return tasks


def prop_title(prop):
    return "".join(t.get("plain_text", "") for t in prop.get("title", []))


def build_properties(task, names, types, status_words):
    """Notion property JSON for one task, using the property names you chose."""
    props = {names["title"]: {"title": [{"text": {"content": task["title"]}}]}}
    if task["due"] and names["date"] in types:
        props[names["date"]] = {"date": {"start": task["due"]}}
    if task["tags"] and names["tags"] in types:
        props[names["tags"]] = {"multi_select": [{"name": t} for t in task["tags"]]}
    if task["priority"] and names["priority"] in types:
        kind = types[names["priority"]]
        props[names["priority"]] = {kind: {"name": task["priority"].capitalize()}}
    status = names["status"]
    if status in types:
        word = status_words[1] if task["done"] else status_words[0]
        props[status] = {types[status]: {"name": word}} if types[status] != "checkbox" else {
            "checkbox": task["done"]}
    return props


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
    parser = argparse.ArgumentParser(description="Import tasks from a text file into Notion.")
    parser.add_argument("file", type=Path, help="text file, one task per line")
    parser.add_argument("--db", help="Notion database id")
    parser.add_argument("--existing", type=Path,
                        help="saved database query (JSON) instead of Notion")
    parser.add_argument("--title-prop", default="Name")
    parser.add_argument("--status-prop", default="Status")
    parser.add_argument("--todo-value", default="Not started", help="status for open tasks")
    parser.add_argument("--done-value", default="Done", help="status for finished tasks")
    parser.add_argument("--date-prop", default="Due")
    parser.add_argument("--tags-prop", default="Tags")
    parser.add_argument("--priority-prop", default="Priority")
    parser.add_argument("--today", help="treat this date as today, YYYY-MM-DD (for testing)")
    parser.add_argument("--delay", type=float, default=0.35, help="seconds between writes (0.35)")
    parser.add_argument("--apply", action="store_true", help="actually create the tasks")
    args = parser.parse_args(argv)
    if not (args.db or args.existing):
        parser.error("give --db DATABASE_ID or --existing FILE")
    if args.apply and not args.db:
        parser.error("--apply needs --db so there is a database to add to")
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")
    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
    except ValueError:
        parser.error("--today must look like 2026-11-09")

    try:
        tasks = parse_tasks(args.file.read_text(encoding="utf-8-sig"), today)
        if args.existing:
            schema, pages = {}, json.loads(args.existing.read_text(encoding="utf-8"))["results"]
        else:
            schema, pages = fetch_database(args.db)
    except urllib.error.HTTPError as err:
        hint = {401: "bad token", 404: "database not found - share it with your integration"}
        print(f"Notion said {err.code} ({hint.get(err.code, err.reason)}).", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError, KeyError) as err:
        print(f"Couldn't read the data: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    types = {name: prop.get("type") for name, prop in schema.items()}
    for page in pages:
        for name, prop in page.get("properties", {}).items():
            types.setdefault(name, prop.get("type"))
    names = {"title": args.title_prop, "status": args.status_prop, "date": args.date_prop,
             "tags": args.tags_prop, "priority": args.priority_prop}
    if types.get(names["title"]) != "title":
        print(f"The database has no title property called '{names['title']}'. "
              "Use --title-prop.", file=sys.stderr)
        return 1
    known = {prop_title(p["properties"][names["title"]]).casefold() for p in pages
             if names["title"] in p["properties"]}
    missing = [n for k, n in names.items() if k != "title" and n not in types]

    fresh = [t for t in tasks if t["title"].casefold() not in known]
    print(f"{len(tasks)} task(s) in the file: {len(fresh)} to add, "
          f"{len(tasks) - len(fresh)} already in Notion.")
    if missing:
        print(f"No such property in the database (ignored): {', '.join(missing)}")
    for task in tasks:
        if task in fresh:
            extras = [f"due {task['due']}" if task["due"] else "",
                      f"tags {','.join(task['tags'])}" if task["tags"] else "",
                      f"priority {task['priority']}" if task["priority"] else "",
                      "done" if task["done"] else ""]
            detail = ", ".join(e for e in extras if e)
            print(f"  + {task['title']}" + (f"  [{detail}]" if detail else ""))
        else:
            print(f"  = {task['title']}  (already there)")
    if not args.apply:
        print("\nDry run - nothing added. Add --apply to create these tasks in Notion.")
        return 0
    try:
        for task in fresh:
            props = build_properties(task, names, types, (args.todo_value, args.done_value))
            notion("POST", "/pages", {"parent": {"database_id": args.db}, "properties": props})
            time.sleep(args.delay)
    except urllib.error.HTTPError as err:
        print(f"Notion said {err.code} while adding; some tasks may already be created.",
              file=sys.stderr)
        return 1
    print(f"\nAdded {len(fresh)} task(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
