"""Assemble one markdown report from a folder (or list) of section files."""
import argparse
import fnmatch
import re
import sys
from datetime import date
from pathlib import Path

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def natural_key(path):
    """Sort 2-intro before 10-outro."""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", path.name)]


def collect(inputs, exclude):
    """Expand folders into their .md files (sorted) and drop excluded names."""
    files = []
    for item in inputs:
        if item.is_dir():
            files += sorted((p for p in item.iterdir() if p.suffix.lower() == ".md"),
                            key=natural_key)
        elif item.is_file():
            files.append(item)
        else:
            raise FileNotFoundError(f"not found: {item}")
    return [f for f in files if not any(fnmatch.fnmatch(f.name, pat) for pat in exclude)]


def split_front_matter(text):
    """Return ({key: value}, body) for a leading '---' block; ({}, text) when there is none."""
    lines = text.lstrip("﻿").splitlines()
    if lines and lines[0].strip() == "---":
        for end in range(1, len(lines)):
            if lines[end].strip() == "---":
                meta = {}
                for line in lines[1:end]:
                    key, sep, value = line.partition(":")
                    if sep:
                        meta[key.strip().lower()] = value.strip().strip("\"'")
                return meta, "\n".join(lines[end + 1:]).strip("\n")
    return {}, text.strip("\n")


def slug(title, used):
    """GitHub-style anchor, made unique when a heading repeats."""
    base = re.sub(r"[^\w\- ]", "", title.lower()).strip().replace(" ", "-") or "section"
    count = used.get(base, 0)
    used[base] = count + 1
    return base if not count else f"{base}-{count}"


def headings(markdown, deepest):
    found, in_code = [], False
    for line in markdown.splitlines():
        if FENCE.match(line):
            in_code = not in_code
        elif not in_code:
            match = HEADING.match(line)
            if match and len(match.group(1)) <= deepest:
                found.append((len(match.group(1)), re.sub(r"[*_`]", "", match.group(2))))
    return found


def table_of_contents(markdown, deepest):
    used, lines = {}, ["## Contents", ""]
    for level, title in headings(markdown, deepest):
        lines.append(f"{'  ' * (level - 1)}- [{title}](#{slug(title, used)})")
    return "\n".join(lines)


def build(files, title, author, day, toc, deepest):
    """Return (markdown, titles of the files used)."""
    meta, parts = {}, []
    for file in files:
        found, body = split_front_matter(file.read_text(encoding="utf-8"))
        meta = {**found, **meta}  # the first file to set a key wins
        if body.strip():
            parts.append(body)
    title = title or meta.get("title") or "Report"
    author = author or meta.get("author")
    byline = " | ".join(x for x in (author, str(day)) if x)
    body = "\n\n".join(parts)
    head = [f"# {title}", "", f"*{byline}*"]
    if toc and headings(body, deepest):
        head += ["", table_of_contents(body, deepest)]
    return "\n".join(head) + "\n\n" + body + "\n", [f.name for f in files]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a markdown report from section files.")
    parser.add_argument("sections", nargs="+", type=Path, help="markdown files or folders")
    parser.add_argument("--title", help="report title (default: from front matter)")
    parser.add_argument("--author", help="author line (default: from front matter)")
    parser.add_argument("--date", help="date shown under the title, YYYY-MM-DD (today)")
    parser.add_argument("--toc", action="store_true", help="add a table of contents")
    parser.add_argument("--toc-depth", type=int, default=2, help="deepest heading listed (2)")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                        help="skip file names matching this, e.g. 'draft*' (repeatable)")
    parser.add_argument("--output", type=Path, help="write this new file instead of printing")
    parser.add_argument("--force", action="store_true", help="overwrite --output if it exists")
    args = parser.parse_args(argv)
    if not 1 <= args.toc_depth <= 6:
        parser.error("--toc-depth must be between 1 and 6")
    try:
        day = date.fromisoformat(args.date) if args.date else date.today()
    except ValueError:
        parser.error(f"--date must look like 2026-11-23, got '{args.date}'")
    if args.output and args.output.exists() and not args.force:
        print(f"{args.output} already exists; use --force to overwrite it.", file=sys.stderr)
        return 1
    try:
        files = collect(args.sections, args.exclude)
        if not files:
            print("No markdown files to combine.", file=sys.stderr)
            return 1
        markdown, used = build(files, args.title, args.author, day, args.toc, args.toc_depth)
    except (OSError, UnicodeDecodeError) as err:
        print(f"Can't build the report: {err}", file=sys.stderr)
        return 1
    if args.output:
        args.output.write_text(markdown, encoding="utf-8")
        print(f"Wrote {args.output} from {len(used)} file(s): {', '.join(used)}")
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
