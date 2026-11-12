"""Bucket log events into a timeline so bursts and quiet gaps stand out."""
import argparse
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})")
NGINX = re.compile(r"\[(\d{2})/([A-Za-z]{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2})")
SYSLOG = re.compile(r"^([A-Za-z]{3})\s+(\d{1,2}) (\d{2}):(\d{2}):(\d{2})")
LEVEL = re.compile(r"\b(TRACE|DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|ERR|CRITICAL|FATAL|SEVERE)\b",
                   re.IGNORECASE)
CANONICAL = {"WARN": "WARNING", "ERR": "ERROR", "FATAL": "CRITICAL", "SEVERE": "CRITICAL"}
LETTERS = {"TRACE": "T", "DEBUG": "D", "INFO": "I", "NOTICE": "N", "WARNING": "W", "ERROR": "E",
           "CRITICAL": "C"}
BUCKET = re.compile(r"(\d+)\s*(s|m|h|d)", re.IGNORECASE)
MAX_ROWS = 500


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


def parse_bucket(text):
    """'10m' -> timedelta(minutes=10). Accepts seconds, minutes, hours and days."""
    match = BUCKET.fullmatch(text.strip())
    if not match or int(match.group(1)) < 1:
        raise argparse.ArgumentTypeError("bucket must look like 30s, 10m, 1h or 1d")
    unit = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}[match.group(2).lower()]
    return timedelta(**{unit: int(match.group(1))})


def floor_time(when, size):
    """Round a time down to the start of its bucket (buckets are counted from midnight)."""
    seconds = int(size.total_seconds())
    midnight = when.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed = int((when - midnight).total_seconds())
    if seconds >= 86400:
        days = seconds // 86400
        return midnight - timedelta(days=(midnight.toordinal() % days))
    return midnight + timedelta(seconds=elapsed - elapsed % seconds)


def collect(lines, year, size, level=None, pattern=None):
    """Return (Counter of bucket start -> events, {bucket: Counter of levels}, skipped lines)."""
    counts, levels, skipped = Counter(), {}, 0
    wanted = CANONICAL.get(level, level) if level else None
    for line in lines:
        when = parse_time(line, year)
        if when is None:
            skipped += 1
            continue
        found = LEVEL.search(line)
        name = CANONICAL.get(found.group(1).upper(), found.group(1).upper()) if found else None
        if wanted and name != wanted:
            continue
        if pattern and not pattern.search(line):
            continue
        bucket = floor_time(when, size)
        counts[bucket] += 1
        levels.setdefault(bucket, Counter())[name] += 1
    return counts, levels, skipped


def render(counts, levels, size, width, fill):
    if not counts:
        return []
    start, end = min(counts), max(counts)
    rows, current = [], start
    if fill:
        total_rows = int((end - start) / size) + 1
        if total_rows > MAX_ROWS:
            raise ValueError(f"that would need {total_rows} rows; use a bigger --bucket "
                             f"(the limit is {MAX_ROWS})")
        while current <= end:
            rows.append(current)
            current += size
    else:
        rows = sorted(counts)
    peak = max(counts.values())
    pattern = "%Y-%m-%d" if size >= timedelta(days=1) else "%Y-%m-%d %H:%M"
    lines = []
    for bucket in rows:
        count = counts.get(bucket, 0)
        bar = "#" * max(1, round(count / peak * width)) if count else ""
        mix = " ".join(f"{LETTERS.get(name, '?')}{n}" for name, n in sorted(
            levels.get(bucket, {}).items(), key=lambda kv: (-kv[1], str(kv[0]))) if name)
        flag = "  <-- peak" if count == peak else ""
        stamp = bucket.strftime(pattern)
        lines.append(f"{stamp}  {count:>5}  {bar:<{width}}  {mix}{flag}".rstrip())
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bucket log events into a timeline.")
    parser.add_argument("files", nargs="+", type=Path, help="log file(s)")
    parser.add_argument("--bucket", type=parse_bucket, default=timedelta(hours=1),
                        help="bucket size: 30s, 10m, 1h, 1d... (1h)")
    parser.add_argument("--level", choices=list(LETTERS), help="count only this level")
    parser.add_argument("--pattern", help="count only lines matching this regex")
    parser.add_argument("--width", type=int, default=30, help="bar width (30)")
    parser.add_argument("--no-fill", action="store_true", help="hide empty buckets")
    parser.add_argument("--year", type=int, default=datetime.now().year,
                        help="year to assume for syslog-style dates")
    args = parser.parse_args(argv)
    if args.width < 5:
        parser.error("--width must be at least 5")
    try:
        pattern = re.compile(args.pattern) if args.pattern else None
    except re.error as err:
        parser.error(f"bad --pattern: {err}")
    lines = []
    for path in args.files:
        try:
            lines += path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as err:
            print(f"Couldn't read {path}: {err.strerror or err}", file=sys.stderr)
            return 1

    counts, levels, skipped = collect(lines, args.year, args.bucket, args.level, pattern)
    if not counts:
        print("No matching events with a recognisable timestamp were found.")
        return 1
    try:
        rows = render(counts, levels, args.bucket, args.width, not args.no_fill)
    except ValueError as err:
        print(err, file=sys.stderr)
        return 1
    note = f" ({skipped} line(s) without a timestamp skipped)" if skipped else ""
    print(f"{sum(counts.values()):,} event(s) in {len(counts)} bucket(s) of {args.bucket}{note}")
    print("\n".join(rows))
    print("\nLetters show levels: T trace, D debug, I info, N notice, W warning, E error, "
          "C critical.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
