"""Build a table of contents for a markdown file, optionally writing it into the file."""
import argparse
import re
import sys
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
START, END = "<!-- TOC -->", "<!-- /TOC -->"


def slugify(title, seen):
    """GitHub-style anchor; repeated titles get -1, -2 and so on."""
    slug = re.sub(r"[^\w\- ]", "", title.lower()).strip().replace(" ", "-")
    count = seen.get(slug, 0)
    seen[slug] = count + 1
    return slug if count == 0 else f"{slug}-{count}"


def find_headings(text):
    """Return (level, title, anchor) for each heading, skipping fenced code blocks."""
    headings, seen, fenced = [], {}, False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced and (match := HEADING_RE.match(line)):
            title = match.group(2)
            headings.append((len(match.group(1)), title, slugify(title, seen)))
    return headings


def build_toc(headings, min_level=2, max_level=3):
    chosen = [h for h in headings if min_level <= h[0] <= max_level]
    if not chosen:
        return ""
    base = min(level for level, _, _ in chosen)
    return "\n".join(f"{'  ' * (level - base)}- [{title}](#{anchor})"
                     for level, title, anchor in chosen)


def insert_toc(text, toc):
    """Replace the block between the TOC markers, or add one under the first heading."""
    block = f"{START}\n{toc}\n{END}"
    if START in text and END in text:
        before, rest = text.split(START, 1)
        return before + block + rest.split(END, 1)[1]
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if HEADING_RE.match(line):
            lines[index + 1:index + 1] = ["", block]
            return "\n".join(lines) + "\n"
    return block + "\n\n" + text


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a markdown table of contents.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--min-level", type=int, default=2, help="first heading level (default 2)")
    parser.add_argument("--max-level", type=int, default=3, help="last heading level (default 3)")
    parser.add_argument("--apply", action="store_true",
                        help="write the TOC into the file (default just prints it)")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")

    text = args.file.read_text(encoding="utf-8")
    toc = build_toc(find_headings(text), args.min_level, args.max_level)
    if not toc:
        print("No headings found in that level range.")
        return 1
    print(toc)
    if args.apply:
        args.file.write_text(insert_toc(text, toc), encoding="utf-8")
        print(f"\nWrote the table of contents into {args.file}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
