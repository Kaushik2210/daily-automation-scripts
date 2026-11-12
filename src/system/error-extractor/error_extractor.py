"""Pull the error entries out of log files, with surrounding lines and whole stack traces."""
import argparse
import re
import sys
from pathlib import Path

TIME_START = re.compile(
    r"^\s*(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}|\[\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2}"
    r"|[A-Za-z]{3}\s+\d{1,2} \d{2}:\d{2}:\d{2})")
CANONICAL = {"WARN": "WARNING", "ERR": "ERROR", "FATAL": "CRITICAL", "SEVERE": "CRITICAL"}
LEVEL = re.compile(r"\b(TRACE|DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|ERR|CRITICAL|FATAL|SEVERE)\b",
                   re.IGNORECASE)


def starts_entry(line):
    return bool(TIME_START.match(line))


def level_of(line):
    match = LEVEL.search(line)
    if not match:
        return None
    name = match.group(1).upper()
    return CANONICAL.get(name, name)


def matches(line, levels, pattern):
    if pattern is not None:
        return bool(pattern.search(line))
    return starts_entry(line) and level_of(line) in levels


def find_blocks(lines, levels, pattern, before, after):
    """Return [(first, last, set of matching line numbers)], 0-based and non-overlapping.

    Each match is widened to include its stack trace (the untimestamped lines that follow it), up
    to `after` extra lines, and `before` lines of context above. Overlapping blocks are merged.
    """
    blocks = []
    for number, line in enumerate(lines):
        if not matches(line, levels, pattern):
            continue
        last = number
        while last + 1 < len(lines):
            following = lines[last + 1]
            if starts_entry(following) or not following.strip():
                break
            last += 1
        last = min(last + after, len(lines) - 1)
        first = max(number - before, 0)
        if blocks and first <= blocks[-1][1] + 1:
            blocks[-1] = (blocks[-1][0], max(blocks[-1][1], last), blocks[-1][2] | {number})
        else:
            blocks.append((first, last, {number}))
    return blocks


def format_blocks(name, lines, blocks, show_name):
    out = []
    width = len(str(len(lines)))
    for index, (first, last, hits) in enumerate(blocks):
        if index:
            out.append("--")
        for number in range(first, last + 1):
            mark = ">" if number in hits else " "
            prefix = f"{name}:" if show_name else ""
            out.append(f"{mark} {prefix}{number + 1:>{width}}  {lines[number]}")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract error entries from logs, with context.")
    parser.add_argument("files", nargs="+", type=Path, help="log file(s) to search")
    parser.add_argument("--levels", default="ERROR,CRITICAL",
                        help="levels to extract, comma separated (ERROR,CRITICAL)")
    parser.add_argument("--pattern", help="extract lines matching this regex instead of levels")
    parser.add_argument("-i", "--ignore-case", action="store_true",
                        help="make --pattern ignore case")
    parser.add_argument("--before", type=int, default=2, help="lines of context before (2)")
    parser.add_argument("--after", type=int, default=0,
                        help="extra lines after, on top of the stack trace (0)")
    parser.add_argument("--count", action="store_true", help="only count the matching entries")
    parser.add_argument("--out", type=Path, help="write the result to this new file")
    args = parser.parse_args(argv)
    if args.before < 0 or args.after < 0:
        parser.error("--before and --after can't be negative")
    try:
        pattern = (re.compile(args.pattern, re.IGNORECASE if args.ignore_case else 0)
                   if args.pattern else None)
    except re.error as err:
        parser.error(f"bad --pattern: {err}")
    levels = {CANONICAL.get(x.strip().upper(), x.strip().upper())
              for x in args.levels.split(",") if x.strip()}
    if args.out and args.out.exists():
        print(f"{args.out} already exists - pick a new name so nothing is overwritten.")
        return 1

    output, total = [], 0
    for path in args.files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as err:
            print(f"Couldn't read {path}: {err.strerror or err}", file=sys.stderr)
            return 1
        blocks = find_blocks(lines, levels, pattern, args.before, args.after)
        total += sum(len(hits) for _, _, hits in blocks)
        if blocks and not args.count:
            if len(args.files) > 1:
                output.append(f"==== {path} ====")
            output += format_blocks(path.name, lines, blocks, len(args.files) > 1)
    summary = f"{total} matching entr{'y' if total == 1 else 'ies'} found."
    if args.count:
        print(summary)
    elif args.out:
        args.out.write_text("\n".join(output) + ("\n" if output else ""), encoding="utf-8")
        print(f"{summary} Saved to {args.out}.")
    else:
        if output:
            print("\n".join(output))
            print()
        print(summary)
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
