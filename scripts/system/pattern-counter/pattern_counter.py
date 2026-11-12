"""Count regex matches across many log files (plain or .gz), per file and in total."""
import argparse
import gzip
import re
import sys
from collections import Counter
from pathlib import Path


def open_text(path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open(encoding="utf-8", errors="replace")


def find_files(paths, glob, recursive):
    found = []
    for path in paths:
        if path.is_dir():
            pattern = f"**/{glob}" if recursive else glob
            found += sorted(p for p in path.glob(pattern) if p.is_file())
        elif path.is_file():
            found.append(path)
    return found


def parse_patterns(specs, flags):
    """Each spec is 'regex' or 'name=regex'. Returns [(label, compiled)]."""
    patterns = []
    for spec in specs:
        label, sep, text = spec.partition("=")
        if not sep or not label.isidentifier():  # no name, or the '=' belongs to the regex
            label, text = spec, spec
        short = label if len(label) <= 24 else label[:21] + "..."
        patterns.append((short, re.compile(text, flags)))
    return patterns


def count_file(path, patterns):
    """Return ({label: matching lines}, {label: Counter of first captured group}, lines read)."""
    lines_hit = {label: 0 for label, _ in patterns}
    captured = {label: Counter() for label, _ in patterns}
    total = 0
    with open_text(path) as handle:
        for line in handle:
            total += 1
            for label, regex in patterns:
                match = regex.search(line)
                if match:
                    lines_hit[label] += 1
                    if regex.groups:
                        captured[label][match.group(1) or ""] += 1
    return lines_hit, captured, total


def main(argv=None):
    parser = argparse.ArgumentParser(description="Count regex matches across log files.")
    parser.add_argument("paths", nargs="+", type=Path, help="log files or folders of logs")
    parser.add_argument("-p", "--pattern", action="append", required=True, metavar="[NAME=]REGEX",
                        help="what to count; repeat for several, e.g. -p timeouts=timeout")
    parser.add_argument("-i", "--ignore-case", action="store_true", help="ignore case")
    parser.add_argument("--glob", default="*.log*",
                        help="which files in a folder to read (*.log* also finds .log.1.gz)")
    parser.add_argument("-r", "--recursive", action="store_true", help="search folders recursively")
    parser.add_argument("--top", type=int, default=5,
                        help="values to list for patterns with a (group) (5, 0 = none)")
    args = parser.parse_args(argv)
    if args.top < 0:
        parser.error("--top can't be negative")
    try:
        patterns = parse_patterns(args.pattern, re.IGNORECASE if args.ignore_case else 0)
    except re.error as err:
        parser.error(f"bad pattern: {err}")
    for path in args.paths:
        if not path.exists():
            parser.error(f"not found: {path}")
    files = find_files(args.paths, args.glob, args.recursive)
    if not files:
        print("No log files found.")
        return 1

    labels = [label for label, _ in patterns]
    totals, values = Counter(), {label: Counter() for label in labels}
    rows, unreadable, lines_read = [], 0, 0
    for path in files:
        try:
            hits, captured, lines = count_file(path, patterns)
        except (OSError, EOFError) as err:
            print(f"Couldn't read {path.name}: {getattr(err, 'strerror', None) or err}",
                  file=sys.stderr)
            unreadable += 1
            continue
        rows.append((path.name, hits, lines))
        lines_read += lines
        for label in labels:
            totals[label] += hits[label]
            values[label].update(captured[label])

    name_width = max(len("File"), *(len(name) for name, _, _ in rows))
    col = [max(len(label), 6) for label in labels]
    header = f"{'File':<{name_width}}  {'Lines':>7}  " + "  ".join(
        f"{label:>{w}}" for label, w in zip(labels, col, strict=True))
    print(header)
    for name, hits, lines in rows:
        print(f"{name:<{name_width}}  {lines:>7,}  " + "  ".join(
            f"{hits[label]:>{w},}" for label, w in zip(labels, col, strict=True)))
    if len(rows) > 1:
        print(f"{'TOTAL':<{name_width}}  {lines_read:>7,}  " + "  ".join(
            f"{totals[label]:>{w},}" for label, w in zip(labels, col, strict=True)))
    if args.top:
        for label, regex in patterns:
            if regex.groups and values[label]:
                shown = ", ".join(f"{v or '(empty)'} ({n})"
                                  for v, n in values[label].most_common(args.top))
                print(f"\nTop values for {label}: {shown}")
    return 1 if unreadable else 0 if sum(totals.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
