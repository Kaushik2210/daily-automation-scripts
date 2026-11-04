"""A simple add / list / done / remove task manager. Tasks live in a small JSON file."""
import argparse
import json
import sys
from pathlib import Path

DEFAULT_FILE = Path.home() / ".todos.json"
PRIORITIES = ["high", "normal", "low"]
ACTIONS = ["add", "list", "done", "undo", "remove", "clear-done"]


def load(path):
    if not path.exists():
        return {"next_id": 1, "todos": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def add_todo(data, text, priority="normal"):
    todo = {"id": data["next_id"], "text": text, "priority": priority, "done": False}
    data["todos"].append(todo)
    data["next_id"] += 1
    return todo


def find(data, todo_id):
    for todo in data["todos"]:
        if todo["id"] == todo_id:
            return todo
    raise KeyError(todo_id)


def sorted_todos(data, show_done=False):
    """Open tasks first by priority, then by id; finished ones only when asked for."""
    rank = {name: i for i, name in enumerate(PRIORITIES)}
    items = [t for t in data["todos"] if show_done or not t["done"]]
    return sorted(items, key=lambda t: (t["done"], rank[t["priority"]], t["id"]))


def render(todos):
    lines = []
    for t in todos:
        mark = "x" if t["done"] else " "
        flag = "!" if t["priority"] == "high" and not t["done"] else " "
        lines.append(f"[{mark}] {t['id']:>3} {flag} {t['text']}")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="Tiny task manager.")
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument("text", nargs="*",
                        help="task text (add) or task numbers (done, undo, remove)")
    parser.add_argument("-p", "--priority", choices=PRIORITIES, default="normal",
                        help="priority for a new task")
    parser.add_argument("-a", "--all", action="store_true", help="include finished tasks in list")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE,
                        help=f"data file (default: {DEFAULT_FILE})")
    args = parser.parse_args(argv)
    data = load(args.file)

    if args.action == "add":
        if not args.text:
            parser.error("add needs the task text")
        todo = add_todo(data, " ".join(args.text), args.priority)
        save(args.file, data)
        print(f"Added #{todo['id']}: {todo['text']}")
    elif args.action in ("done", "undo", "remove"):
        try:
            ids = [int(x) for x in args.text]
        except ValueError:
            parser.error(f"{args.action} needs task numbers, like: {args.action} 3")
        if not ids:
            parser.error(f"{args.action} needs at least one task number")
        for todo_id in ids:
            try:
                todo = find(data, todo_id)
            except KeyError:
                print(f"No task #{todo_id}.", file=sys.stderr)
                return 1
            if args.action == "remove":
                data["todos"].remove(todo)
            else:
                todo["done"] = args.action == "done"
            print(f"{args.action} #{todo_id}: {todo['text']}")
        save(args.file, data)
    elif args.action == "clear-done":
        before = len(data["todos"])
        data["todos"] = [t for t in data["todos"] if not t["done"]]
        save(args.file, data)
        print(f"Removed {before - len(data['todos'])} finished task(s).")
    else:
        todos = sorted_todos(data, args.all)
        print("\n".join(render(todos)) if todos else "Nothing to do!")
        open_count = sum(not t["done"] for t in data["todos"])
        print(f"{open_count} open, {len(data['todos']) - open_count} done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
