"""Create a calendar (.ics) file with events from a CSV, ready for any calendar app."""
import argparse
import contextlib
import csv
import hashlib
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

with contextlib.suppress(ImportError):
    import tzdata  # noqa: F401  (supplies the zone database on Windows and in the browser)

ALIASES = {"title": ("title", "summary", "name", "event"), "start": ("start", "begin", "date"),
           "end": ("end", "finish"), "location": ("location", "place", "where"),
           "description": ("description", "notes", "details")}


def parse_when(text):
    """'2026-11-16 09:30' or '2026-11-16T09:30' -> datetime; '2026-11-16' -> date (all day)."""
    text = text.strip().replace("T", " ")
    if len(text) == 10:
        return date.fromisoformat(text)
    return datetime.fromisoformat(text)


def escape(text):
    return (text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\\n").replace("\n", "\\n"))


def fold(line):
    """Lines in an .ics file may be at most 75 bytes; continue long ones after CRLF + space."""
    raw, parts = line.encode("utf-8"), []
    while len(raw) > 75:
        cut = 75
        while raw[cut] & 0xC0 == 0x80:  # don't split a multi-byte character
            cut -= 1
        parts.append(raw[:cut].decode("utf-8"))
        raw = b" " + raw[cut:]
    parts.append(raw.decode("utf-8"))
    return "\r\n".join(parts)


def pick(row, field):
    lowered = {key.strip().lower(): value for key, value in row.items() if key}
    for name in ALIASES[field]:
        if (lowered.get(name) or "").strip():
            return lowered[name].strip()
    return ""


def stamp_for(moment, zone, to_utc):
    """Format one start/end value; returns (property suffix, value text)."""
    if isinstance(moment, datetime):
        if zone and to_utc:
            return "", moment.replace(tzinfo=zone).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        if zone:
            return f";TZID={zone.key}", moment.strftime("%Y%m%dT%H%M%S")
        return "", moment.strftime("%Y%m%dT%H%M%S")
    return ";VALUE=DATE", moment.strftime("%Y%m%d")


def make_event(row, zone, to_utc, minutes, alarm, now):
    title, start_text = pick(row, "title"), pick(row, "start")
    if not title or not start_text:
        raise ValueError("needs a title and a start")
    start = parse_when(start_text)
    end_text = pick(row, "end")
    if end_text:
        end = parse_when(end_text)
    else:
        end = start + (timedelta(days=1) if not isinstance(start, datetime)
                       else timedelta(minutes=minutes))
    if isinstance(start, datetime) != isinstance(end, datetime):
        raise ValueError("start and end must both be dates or both be date-times")
    if end < start:
        raise ValueError("ends before it starts")
    uid = hashlib.sha1(f"{title}|{start_text}".encode()).hexdigest()[:20]
    s_prop, s_val = stamp_for(start, zone, to_utc)
    e_prop, e_val = stamp_for(end, zone, to_utc)
    lines = ["BEGIN:VEVENT", f"UID:{uid}@daily-automation-scripts",
             f"DTSTAMP:{now:%Y%m%dT%H%M%SZ}", f"DTSTART{s_prop}:{s_val}", f"DTEND{e_prop}:{e_val}",
             f"SUMMARY:{escape(title)}"]
    for field, key in (("location", "LOCATION"), ("description", "DESCRIPTION")):
        if pick(row, field):
            lines.append(f"{key}:{escape(pick(row, field))}")
    if alarm and isinstance(start, datetime):
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{escape(title)}",
                  f"TRIGGER:-PT{alarm}M", "END:VALARM"]
    lines.append("END:VEVENT")
    return lines


def build_calendar(rows, zone=None, to_utc=False, minutes=60, alarm=0, now=None, name="Events"):
    """Return (ics text, [(row number, problem)]) for the rows that could be converted."""
    now = now or datetime.now(UTC)
    body, problems = [], []
    for number, row in enumerate(rows, 2):
        try:
            body += make_event(row, zone, to_utc, minutes, alarm, now)
        except ValueError as err:
            problems.append((number, str(err)))
    head = ["BEGIN:VCALENDAR", "VERSION:2.0",
            "PRODID:-//daily-automation-scripts//ics-generator//EN", "CALSCALE:GREGORIAN",
            f"X-WR-CALNAME:{escape(name)}"]
    return "\r\n".join(fold(line) for line in head + body + ["END:VCALENDAR"]) + "\r\n", problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create calendar .ics events from a CSV.")
    parser.add_argument("csv", type=Path, help="CSV with title,start[,end,location,description]")
    parser.add_argument("--out", type=Path, help="write to this new .ics file instead of printing")
    parser.add_argument("--tz", help="time zone of the times, e.g. Europe/London (default: none)")
    parser.add_argument("--utc", action="store_true", help="convert times to UTC (needs --tz)")
    parser.add_argument("--minutes", type=int, default=60, help="length when no end is given (60)")
    parser.add_argument("--alarm", type=int, default=0, help="remind this many minutes before")
    parser.add_argument("--name", default="Events", help="calendar name")
    parser.add_argument("--stamp", help="fixed creation time YYYY-MM-DDTHH:MM (for testing)")
    args = parser.parse_args(argv)
    if args.utc and not args.tz:
        parser.error("--utc needs --tz so the tool knows which zone to convert from")
    if not args.csv.is_file():
        parser.error(f"not a file: {args.csv}")
    if args.out and args.out.exists():
        print(f"{args.out} already exists - pick a new name so nothing is overwritten.")
        return 1
    try:
        zone = ZoneInfo(args.tz) if args.tz else None
        now = datetime.fromisoformat(args.stamp).replace(tzinfo=UTC) if args.stamp else None
    except (ZoneInfoNotFoundError, ValueError) as err:
        parser.error(f"bad --tz or --stamp: {err}")
    with args.csv.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    text, problems = build_calendar(rows, zone, args.utc, args.minutes, args.alarm, now, args.name)
    for number, problem in problems:
        print(f"row {number} skipped: {problem}", file=sys.stderr)
    made = len(rows) - len(problems)
    if not made:
        print("No events could be made from that CSV.", file=sys.stderr)
        return 1
    if args.out:
        args.out.write_text(text, encoding="utf-8", newline="")
        print(f"Wrote {made} event(s) to {args.out}.")
    else:
        print(text.replace("\r\n", "\n"), end="")  # the terminal adds its own line endings
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
