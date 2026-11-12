"""Merge several log files into one, in timestamp order, keeping multi-line entries together."""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})")
NGINX = re.compile(r"\[(\d{2})/([A-Za-z]{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2})")
SYSLOG = re.compile(r"^([A-Za-z]{3})\s+(\d{1,2}) (\d{2}):(\d{2}):(\d{2})")


def parse_time(line, year):
    try:
        if match := ISO.search(line[:40]):
            return datetime(*map(int, match.groups()))
        if match := NGINX.search(line[:60]):
            day, month, yr, hour, minute, second = match.groups()
            return datetime(int(yr), MONTHS[month.title()], int(day), int(hour), int(minute),
                            int(second))
        if match := SYSLOG.match(line):
            month, day, hour, minute, second = match.groups()
            return datetime(year, MONTHS[month.title()], int(day), int(hour), int(minute),
                            int(second))
    except (ValueError, KeyError):
        return None
    return None


def read_entries(path, year):
    """Return a list of (time, [lines]); untimestamped lines join the entry above them."""
    entries, stray = [], []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        when = parse_time(line, year)
        if when is not None:
            entries.append([when, [line]])
        elif entries:
            entries[-1][1].append(line)
        else:
            stray.append(line)
    if stray:  # lines before the first timestamp: keep them ahead of the file's first entry
        first = entries[0][0] if entries else datetime.min
        entries.insert(0, [first, stray])
    return [(when, lines) for when, lines in entries]


def merge(sources, label=False):
    """sources: [(name, entries)]. Returns (merged lines, count of out-of-order entries fixed)."""
    keyed, disordered = [], 0
    for order, (name, entries) in enumerate(sources):
        previous = None
        for position, (when, lines) in enumerate(entries):
            if previous and when < previous:
                disordered += 1
            previous = max(previous or when, when)
            keyed.append((when, order, position, name, lines))
    keyed.sort(key=lambda item: item[:3])  # time, then file order, then original position
    merged = []
    for _when, _order, _position, name, lines in keyed:
        merged += [f"[{name}] {line}" if label else line for line in lines]
    return merged, disordered


def main(argv=None):
    parser = argparse.ArgumentParser(description="Merge logs in timestamp order.")
    parser.add_argument("files", nargs="+", type=Path, help="two or more log files")
    parser.add_argument("--label", action="store_true", help="prefix each line with its file name")
    parser.add_argument("--since", help="drop entries before this time, e.g. '2026-11-10 09:05'")
    parser.add_argument("--until", help="drop entries after this time")
    parser.add_argument("--out", type=Path, help="write the merged log to this new file")
    parser.add_argument("--year", type=int, default=datetime.now().year,
                        help="year to assume for syslog-style dates")
    args = parser.parse_args(argv)
    try:
        since = datetime.fromisoformat(args.since) if args.since else None
        until = datetime.fromisoformat(args.until) if args.until else None
    except ValueError:
        parser.error("--since and --until must look like '2026-11-10 09:05'")
    if args.out and args.out.exists():
        print(f"{args.out} already exists - pick a new name so nothing is overwritten.")
        return 1

    sources = []
    for path in args.files:
        try:
            entries = read_entries(path, args.year)
        except OSError as err:
            print(f"Couldn't read {path}: {err.strerror or err}", file=sys.stderr)
            return 1
        entries = [(w, ln) for w, ln in entries
                   if (not since or w >= since) and (not until or w <= until)]
        sources.append((path.stem, entries))
    merged, disordered = merge(sources, args.label)
    if not merged:
        print("No log entries to merge.", file=sys.stderr)
        return 1
    note = f"Merged {sum(len(e) for _, e in sources)} entries from {len(sources)} file(s)"
    if disordered:
        note += f"; {disordered} entry/entries were out of order in their own file and were sorted"
    if args.out:
        args.out.write_text("\n".join(merged) + "\n", encoding="utf-8")
        print(f"{note}. Saved to {args.out}.")
    else:
        print("\n".join(merged))
        print(note + ".", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
