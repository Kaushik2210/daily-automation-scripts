"""Summarize a log file: levels, time span, busiest hours and the most common errors."""
import argparse
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})")
NGINX = re.compile(r"\[(\d{2})/([A-Za-z]{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2})")
SYSLOG = re.compile(r"^([A-Za-z]{3})\s+(\d{1,2}) (\d{2}):(\d{2}):(\d{2})")
LEVEL = re.compile(r"\b(TRACE|DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|ERR|CRITICAL|FATAL|SEVERE)\b",
                   re.IGNORECASE)
CANONICAL = {"WARN": "WARNING", "ERR": "ERROR", "FATAL": "CRITICAL", "SEVERE": "CRITICAL"}
ORDER = ["TRACE", "DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL"]


def parse_time(line, year):
    """Return the datetime found at the start of a log line, or None if it has none."""
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


def parse_level(line):
    match = LEVEL.search(line)
    if not match:
        return None
    name = match.group(1).upper()
    return CANONICAL.get(name, name)


def parse_entries(lines, year):
    """Group lines into entries; lines without a timestamp (stack traces) join the entry above."""
    entries, orphans = [], 0
    for line in lines:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        when = parse_time(line, year)
        if when is None:
            if entries:
                entries[-1]["extra"] += 1
            else:
                orphans += 1
            continue
        entries.append({"time": when, "level": parse_level(line), "text": line, "extra": 0})
    return entries, orphans


def normalise(text):
    """Strip the timestamp, level and variable numbers so repeats of one problem group together."""
    text = ISO.sub("", text, count=1)
    text = re.sub(r"^[\s,.\d:]*", "", text)
    text = LEVEL.sub("", text, count=1)
    text = re.sub(r"\[[^\]]*\]", "", text, count=1)
    text = re.sub(r"0x[0-9a-fA-F]+|\d+", "#", text)
    return " ".join(text.split())[:100]


def summarize(entries):
    levels = Counter(e["level"] or "(none)" for e in entries)
    hours = Counter(e["time"].replace(minute=0, second=0) for e in entries)
    errors = Counter(normalise(e["text"]) for e in entries if e["level"] in ("ERROR", "CRITICAL"))
    return levels, hours, errors


def bar(count, biggest, width=24):
    return "#" * max(1, round(count / biggest * width)) if count else ""


def report(entries, orphans, top):
    lines = []
    first, last = min(e["time"] for e in entries), max(e["time"] for e in entries)
    levels, hours, errors = summarize(entries)
    lines.append(f"{len(entries):,} entries from {first:%Y-%m-%d %H:%M:%S} to "
                 f"{last:%Y-%m-%d %H:%M:%S}" + (f" ({orphans} stray line(s) ignored)" if orphans
                                                 else ""))
    traces = sum(e["extra"] for e in entries)
    if traces:
        lines.append(f"{traces:,} continuation line(s) such as stack traces were attached to the "
                     "entry above them.")
    lines.append("\nLevels:")
    names = [n for n in ORDER if n in levels] + sorted(n for n in levels if n not in ORDER)
    biggest = max(levels.values())
    for name in names:
        share = levels[name] / len(entries)
        lines.append(f"  {name:<9} {levels[name]:>6,}  {share:>6.1%}  {bar(levels[name], biggest)}")
    lines.append(f"\nBusiest hours (top {min(top, len(hours))}):")
    peak = max(hours.values())
    for hour, count in sorted(hours.items(), key=lambda h: (-h[1], h[0]))[:top]:
        lines.append(f"  {hour:%Y-%m-%d %H}:00  {count:>6,}  {bar(count, peak)}")
    if errors:
        lines.append(f"\nMost common errors (top {min(top, len(errors))}):")
        for message, count in errors.most_common(top):
            lines.append(f"  {count:>5,}x  {message}")
    else:
        lines.append("\nNo ERROR or CRITICAL entries.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarize one or more log files.")
    parser.add_argument("files", nargs="+", type=Path, help="log file(s) to analyze")
    parser.add_argument("--top", type=int, default=5, help="rows in the top lists (5)")
    parser.add_argument("--year", type=int, default=datetime.now().year,
                        help="year to assume for syslog-style dates (this year)")
    args = parser.parse_args(argv)
    if args.top < 1:
        parser.error("--top must be at least 1")
    lines = []
    for path in args.files:
        try:
            lines += path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as err:
            print(f"Couldn't read {path}: {err.strerror or err}", file=sys.stderr)
            return 1
    entries, orphans = parse_entries(lines, args.year)
    if not entries:
        print("No lines with a recognisable timestamp were found.")
        return 1
    print(report(entries, orphans, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
