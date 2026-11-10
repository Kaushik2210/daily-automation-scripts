"""Generate a weekly review in markdown from your journal, habits, to-dos and notes."""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROMPTS = ["What went well this week?", "What drained my energy?", "What did I learn?",
           "What am I proud of?", "What will I change next week?"]


def monday_of(day):
    return day - timedelta(days=day.weekday())


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as err:
        raise ValueError(f"{path.name} isn't valid JSON ({err.msg})") from None


def journal_entries(text, start, end):
    """Return {date: [entry lines]} for the days of the week found in a markdown journal."""
    days, current = {}, None
    for line in text.splitlines():
        heading = re.match(r"^#{1,3}\s*(\d{4}-\d{2}-\d{2})\s*$", line)
        if heading:
            try:
                current = date.fromisoformat(heading.group(1))
            except ValueError:
                current = None
            continue
        item = re.match(r"^\s*[-*]\s+(.*\S)\s*$", line)
        if current and item and start <= current <= end:
            days.setdefault(current, []).append(item.group(1))
    return dict(sorted(days.items()))


def habit_rows(data, start):
    """Return [(habit, [True/False for Mon..Sun], total)] sorted by total done."""
    rows = []
    for name, done in (data.get("habits") or {}).items():
        marked = {d for d in done}
        flags = [(start + timedelta(days=i)).isoformat() in marked for i in range(7)]
        rows.append((name, flags, sum(flags)))
    return sorted(rows, key=lambda r: (-r[2], r[0]))


def notes_in_week(data, start, end):
    found = []
    for note in data.get("notes") or []:
        try:
            when = datetime.strptime(note["created"][:10], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        if start <= when <= end:
            found.append((when, note.get("text", "")))
    return sorted(found)


def build_review(start, journal="", habits=None, todos=None, notes=None):
    end = start + timedelta(days=6)
    lines = [f"# Weekly review: {start:%d %b} - {end:%d %b %Y}", ""]
    entries = journal_entries(journal, start, end) if journal else {}
    if journal:
        lines += ["## From my journal"]
        for day, items in entries.items():
            lines += [f"**{day:%A %d %b}**"] + [f"- {item}" for item in items] + [""]
        if not entries:
            lines += ["_No journal entries this week._", ""]
    if habits is not None:
        lines += ["## Habits", "", "| Habit | Mo | Tu | We | Th | Fr | Sa | Su | Total |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for name, flags, total in habit_rows(habits, start):
            lines.append(f"| {name} | " + " | ".join("x" if f else "-" for f in flags)
                         + f" | {total}/7 |")
        lines.append("")
    if todos is not None:
        items = todos.get("todos") or []
        done = [t for t in items if t.get("done")]
        open_items = [t for t in items if not t.get("done")]
        order = {"high": 0, "normal": 1, "low": 2}
        lines += ["## To-dos", "", f"Finished: {len(done)} - still open: {len(open_items)}", ""]
        lines += [f"- [x] {t['text']}" for t in done]
        lines += [f"- [ ] {t['text']} ({t.get('priority', 'normal')})"
                  for t in sorted(open_items, key=lambda t: order.get(t.get("priority"), 1))]
        lines.append("")
    if notes is not None:
        captured = notes_in_week(notes, start, end)
        lines += ["## Notes I captured"] + [f"- {when:%a %d %b}: {text}" for when, text in captured]
        if not captured:
            lines.append("_Nothing captured this week._")
        lines.append("")
    lines += ["## Reflect"]
    for prompt in PROMPTS:
        lines += [f"**{prompt}**", "-", ""]
    lines += ["## Top 3 for next week", "- [ ] ", "- [ ] ", "- [ ] ", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a weekly review template.")
    parser.add_argument("--week-of", help="any date in the week to review, YYYY-MM-DD (today)")
    parser.add_argument("--journal", type=Path, help="markdown journal with '## YYYY-MM-DD' days")
    parser.add_argument("--habits", type=Path, help="habits JSON file")
    parser.add_argument("--todos", type=Path, help="to-do JSON file")
    parser.add_argument("--notes", type=Path, help="notes JSON file")
    parser.add_argument("--out", type=Path, help="write to this new markdown file instead")
    args = parser.parse_args(argv)
    try:
        day = date.fromisoformat(args.week_of) if args.week_of else date.today()
    except ValueError:
        parser.error("--week-of must look like 2026-01-07")
    if args.out and args.out.exists():
        print(f"{args.out} already exists - pick a new name so nothing is overwritten.")
        return 1
    for path in (args.journal, args.habits, args.todos, args.notes):
        if path and not path.is_file():
            parser.error(f"not a file: {path}")

    try:
        review = build_review(
            monday_of(day),
            args.journal.read_text(encoding="utf-8-sig") if args.journal else "",
            read_json(args.habits) if args.habits else None,
            read_json(args.todos) if args.todos else None,
            read_json(args.notes) if args.notes else None)
    except (OSError, ValueError, AttributeError) as err:
        print(f"Couldn't read your files: {err}", file=sys.stderr)
        return 1
    if args.out:
        args.out.write_text(review, encoding="utf-8")
        print(f"Wrote the review to {args.out}.")
    else:
        print(review)
    return 0


if __name__ == "__main__":
    sys.exit(main())
