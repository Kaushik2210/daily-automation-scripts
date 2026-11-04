"""Capture and search quick notes from the shell. Notes live in a small JSON file."""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_FILE = Path.home() / ".quick-notes.json"
TAG_RE = re.compile(r"(?<!\w)#([\w-]+)")
ACTIONS = ["add", "list", "search", "delete", "tags"]


def load(path):
    if not path.exists():
        return {"next_id": 1, "notes": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def tags_of(text):
    return sorted({t.lower() for t in TAG_RE.findall(text)})


def add_note(data, text, stamp):
    note = {"id": data["next_id"], "text": text, "created": stamp}
    data["notes"].append(note)
    data["next_id"] += 1
    return note


def select(data, word="", tag=""):
    """Newest-first notes that contain `word` and carry `tag` (both optional)."""
    word, tag = word.lower(), tag.lower().lstrip("#")
    found = [n for n in data["notes"]
             if word in n["text"].lower() and (not tag or tag in tags_of(n["text"]))]
    return sorted(found, key=lambda n: n["id"], reverse=True)


def tag_counts(data):
    counts = {}
    for note in data["notes"]:
        for tag in tags_of(note["text"]):
            counts[tag] = counts.get(tag, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Quick notes for the terminal.")
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument("text", nargs="*", help="note text, search word or note number")
    parser.add_argument("--tag", default="", help="only notes with this #tag (list/search)")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE,
                        help=f"data file (default: {DEFAULT_FILE})")
    parser.add_argument("--stamp", help="timestamp to record instead of now (for testing)")
    args = parser.parse_args(argv)
    data = load(args.file)
    words = " ".join(args.text)

    if args.action == "add":
        if not words:
            parser.error("add needs the note text")
        note = add_note(data, words, args.stamp or datetime.now().strftime("%Y-%m-%d %H:%M"))
        save(args.file, data)
        print(f"Saved note #{note['id']}.")
    elif args.action == "delete":
        if not words.isdigit():
            parser.error("delete needs a note number")
        before = len(data["notes"])
        data["notes"] = [n for n in data["notes"] if n["id"] != int(words)]
        if len(data["notes"]) == before:
            print(f"No note #{words}.", file=sys.stderr)
            return 1
        save(args.file, data)
        print(f"Deleted note #{words}.")
    elif args.action == "tags":
        counts = tag_counts(data)
        print("\n".join(f"#{t}  ({c})" for t, c in counts.items()) if counts else "No tags yet.")
    else:
        if args.action == "search" and not words:
            parser.error("search needs a word to look for")
        notes = select(data, words if args.action == "search" else "", args.tag)
        for n in notes:
            print(f"#{n['id']:<3} {n['created']}  {n['text']}")
        print(f"{len(notes)} note(s).")
        return 0 if notes or args.action == "list" else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
