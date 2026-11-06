"""Append dated, timestamped entries to a markdown journal, and read them back."""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_FILE = Path.home() / "journal.md"
HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$")


def split_sections(text):
    """Return (preamble_lines, [(date, [lines])]) from a journal file."""
    preamble, sections = [], []
    for line in text.splitlines():
        match = HEADING.match(line)
        if match:
            sections.append((match.group(1), []))
        elif sections:
            sections[-1][1].append(line)
        else:
            preamble.append(line)
    return preamble, sections


def join_sections(preamble, sections):
    out = list(preamble) if preamble else ["# Journal"]
    for day, lines in sections:
        body = [ln for ln in lines]
        while body and not body[-1].strip():
            body.pop()
        while body and not body[0].strip():
            body.pop(0)
        out += ["", f"## {day}", ""] + body
    return "\n".join(out).rstrip("\n") + "\n"


def add_entry(text, entry, day, clock):
    """Return the journal text with `entry` added under the heading for `day`."""
    preamble, sections = split_sections(text)
    bullet = f"- {clock} {entry}"
    for date_text, lines in sections:
        if date_text == day:
            lines.append(bullet)
            break
    else:
        sections.append((day, [bullet]))
        sections.sort(key=lambda s: s[0])
    return join_sections(preamble, sections)


def recent(text, days):
    _, sections = split_sections(text)
    return sections[-days:]


def search(text, word):
    needle = word.lower()
    return [(day, ln) for day, lines in split_sections(text)[1] for ln in lines
            if ln.strip() and needle in ln.lower()]


def main(argv=None):
    parser = argparse.ArgumentParser(description="A one-line-at-a-time markdown journal.")
    parser.add_argument("entry", nargs="*", help="text to add (omit to read instead)")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE,
                        help=f"journal file (default: {DEFAULT_FILE})")
    parser.add_argument("--date", help="day for the entry, YYYY-MM-DD (default: today)")
    parser.add_argument("--time", help="time for the entry, HH:MM (default: now)")
    parser.add_argument("--show", type=int, metavar="DAYS", help="show the last N days of entries")
    parser.add_argument("--search", metavar="WORD", help="find entries containing WORD")
    args = parser.parse_args(argv)

    text = args.file.read_text(encoding="utf-8") if args.file.exists() else ""
    if args.search:
        hits = search(text, args.search)
        for day, line in hits:
            print(f"{day}  {line.strip().removeprefix('- ')}")
        print(f"{len(hits)} match(es).")
        return 0 if hits else 1
    if args.show or not args.entry:
        sections = recent(text, args.show or 3)
        for day, lines in sections:
            print(day)
            print("\n".join(ln for ln in lines if ln.strip()))
        print(f"{len(sections)} day(s) shown." if sections else "The journal is empty.")
        return 0

    now = datetime.now()
    day, clock = args.date or now.strftime("%Y-%m-%d"), args.time or now.strftime("%H:%M")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) or not re.fullmatch(r"\d{2}:\d{2}", clock):
        parser.error("use --date YYYY-MM-DD and --time HH:MM")
    args.file.write_text(add_entry(text, " ".join(args.entry), day, clock), encoding="utf-8")
    print(f"Added to {day} at {clock}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
