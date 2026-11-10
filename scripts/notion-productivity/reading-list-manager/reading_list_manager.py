"""Keep a reading list: add books, mark them reading or finished, rate them, see your stats."""
import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

DEFAULT_FILE = Path.home() / ".reading-list.json"
STATUSES = ["reading", "to-read", "done"]
ACTIONS = ["add", "list", "start", "finish", "rate", "remove", "stats"]


def load(path):
    if not path.exists():
        return {"next_id": 1, "books": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("books", [])
    data.setdefault("next_id", max((b["id"] for b in data["books"]), default=0) + 1)
    return data


def save(path, data):
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def add_book(data, title, author="", today=None):
    """Add a book to read; returns None if a book with the same title is already listed."""
    if any(b["title"].casefold() == title.casefold() for b in data["books"]):
        return None
    book = {"id": data["next_id"], "title": title, "author": author, "status": "to-read",
            "rating": None, "added": (today or date.today()).isoformat(), "finished": None}
    data["books"].append(book)
    data["next_id"] += 1
    return book


def find(data, book_id):
    for book in data["books"]:
        if book["id"] == book_id:
            return book
    raise KeyError(book_id)


def describe(book):
    author = f" - {book['author']}" if book.get("author") else ""
    rating = f"  [{book['rating']}/5]" if book.get("rating") else ""
    return f"{book['id']:>3}  {book['title']}{author}{rating}"


def listing(data, status=None):
    lines = []
    for name in STATUSES:
        if status and status != name:
            continue
        books = sorted((b for b in data["books"] if b["status"] == name),
                       key=lambda b: (b.get("finished") or b.get("added") or "", b["id"]),
                       reverse=name == "done")
        if books:
            lines += [f"{name.upper()} ({len(books)})"] + [f"  {describe(b)}" for b in books] + [""]
    return lines


def stats(data):
    books = data["books"]
    counts = Counter(b["status"] for b in books)
    rated = [b["rating"] for b in books if b.get("rating")]
    lines = [f"{len(books)} book(s): {counts['done']} finished, {counts['reading']} reading, "
             f"{counts['to-read']} waiting."]
    if rated:
        average = sum(rated) / len(rated)
        lines.append(f"Average rating: {average:.1f}/5 over {len(rated)} rated book(s).")
    by_month = Counter((b["finished"] or "")[:7] for b in books if b.get("finished"))
    if by_month:
        months = ", ".join(f"{m} ({n})" for m, n in sorted(by_month.items()))
        lines.append(f"Finished by month: {months}")
    best = [b for b in books if b.get("rating") == max(rated or [0])]
    if best and rated:
        lines.append("Top rated: " + "; ".join(b["title"] for b in best))
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="Manage a reading list with statuses.")
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument("words", nargs="*", help="book title (add) or book numbers (the rest)")
    parser.add_argument("--author", default="", help="author for a new book")
    parser.add_argument("--rating", type=int, choices=range(1, 6), metavar="1-5",
                        help="your rating, with finish or rate")
    parser.add_argument("--status", choices=STATUSES, help="only list books with this status")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE,
                        help=f"data file (default: {DEFAULT_FILE})")
    parser.add_argument("--today", help="treat this date as today, YYYY-MM-DD (for testing)")
    args = parser.parse_args(argv)
    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
        data = load(args.file)
    except (ValueError, json.JSONDecodeError, OSError, KeyError, TypeError) as err:
        print(f"Couldn't read the date or the list: {err}", file=sys.stderr)
        return 1

    if args.action == "add":
        if not args.words:
            parser.error("add needs the book title")
        book = add_book(data, " ".join(args.words), args.author, today)
        if book is None:
            print("That title is already on the list.", file=sys.stderr)
            return 1
        save(args.file, data)
        print(f"Added #{book['id']}: {book['title']}")
    elif args.action in ("start", "finish", "rate", "remove"):
        try:
            ids = [int(w) for w in args.words]
        except ValueError:
            parser.error(f"{args.action} needs book numbers, like: {args.action} 3")
        if not ids:
            parser.error(f"{args.action} needs at least one book number")
        if args.action == "rate" and not args.rating:
            parser.error("rate needs --rating 1-5")
        for book_id in ids:
            try:
                book = find(data, book_id)
            except KeyError:
                print(f"No book #{book_id}.", file=sys.stderr)
                return 1
            if args.action == "remove":
                data["books"].remove(book)
            elif args.action == "start":
                book["status"] = "reading"
            elif args.action == "finish":
                book.update(status="done", finished=today.isoformat())
            if args.rating and args.action in ("finish", "rate"):
                book["rating"] = args.rating
            print(f"{args.action} #{book_id}: {book['title']}")
        save(args.file, data)
    elif args.action == "stats":
        print("\n".join(stats(data)) if data["books"] else "The list is empty.")
    else:
        lines = listing(data, args.status)
        print("\n".join(lines).rstrip() if lines else "Nothing on the list yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
