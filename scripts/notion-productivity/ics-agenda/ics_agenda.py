"""Print a daily agenda from an .ics calendar file, including simple repeating events."""
import argparse
import contextlib
import re
import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

with contextlib.suppress(ImportError):
    import tzdata  # noqa: F401  (supplies the zone database on Windows and in the browser)

DAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
MAX_STEPS = 5000


def unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text).replace("\r\n", "\n").split("\n")


def unescape(text):
    return (text.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",")
            .replace("\\;", ";").replace("\\\\", "\\"))


def parse_value(value, params):
    """A DTSTART-style value -> (datetime or date, source zone or None)."""
    value = value.strip()
    if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", value):
        return datetime.strptime(value[:8], "%Y%m%d").date(), None
    zone = None
    if value.endswith("Z"):
        zone, value = UTC, value[:-1]
    elif params.get("TZID"):
        try:
            zone = ZoneInfo(params["TZID"])
        except (ZoneInfoNotFoundError, ValueError):
            zone = None  # unknown zone name: treat the time as local
    return datetime.strptime(value, "%Y%m%dT%H%M%S"), zone


def parse_duration(text):
    match = re.fullmatch(r"([+-])?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?",
                         text.strip())
    if not match:
        return timedelta(0)
    sign = -1 if match.group(1) == "-" else 1
    weeks, days, hours, minutes, seconds = (int(g or 0) for g in match.groups()[1:])
    return sign * timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)


def parse_events(text):
    """Return a list of event dicts from the VEVENT blocks in the calendar text."""
    events, current = [], None
    for line in unfold(text):
        if line == "BEGIN:VEVENT":
            current = {"exdates": []}
        elif line == "END:VEVENT" and current is not None:
            if "start" in current:
                events.append(current)
            current = None
        elif current is not None and ":" in line:
            head, _, value = line.partition(":")
            name, *param_parts = head.split(";")
            params = dict(p.split("=", 1) for p in param_parts if "=" in p)
            name = name.upper()
            try:
                if name == "DTSTART":
                    current["start"], current["zone"] = parse_value(value, params)
                elif name == "DTEND":
                    current["end"], _ = parse_value(value, params)
                elif name == "DURATION":
                    current["duration"] = parse_duration(value)
                elif name == "EXDATE":
                    current["exdates"] += [parse_value(v, params)[0] for v in value.split(",")]
                elif name == "RRULE":
                    current["rrule"] = dict(p.split("=", 1) for p in value.split(";") if "=" in p)
                elif name in ("SUMMARY", "LOCATION", "DESCRIPTION", "STATUS"):
                    current[name.lower()] = unescape(value)
            except ValueError:
                continue  # skip a malformed property rather than the whole calendar
    return events


def event_length(event):
    start = event["start"]
    if "end" in event and isinstance(event["end"], type(start)):
        return event["end"] - start
    return event.get("duration", timedelta(days=1) if not isinstance(start, datetime)
                     else timedelta(0))


def starts(event, until):
    """Yield each occurrence's start (as the event's own date or wall-clock datetime)."""
    first, rule = event["start"], event.get("rrule")
    if not rule:
        yield first
        return
    freq, interval = rule.get("FREQ", ""), max(int(rule.get("INTERVAL", 1)), 1)
    count = int(rule["COUNT"]) if "COUNT" in rule else None
    limit = None
    if "UNTIL" in rule:
        try:
            limit = parse_value(rule["UNTIL"], {})[0]
        except ValueError:
            limit = None
    wall = first if isinstance(first, datetime) else datetime.combine(first, time())
    weekdays = ([DAYS.index(d[-2:]) for d in rule["BYDAY"].split(",") if d[-2:] in DAYS]
                if "BYDAY" in rule else [first.weekday()])
    produced = 0
    for step in range(MAX_STEPS):
        if freq == "DAILY":
            candidates = [wall + timedelta(days=step * interval)]
        elif freq == "WEEKLY":
            monday = wall - timedelta(days=wall.weekday()) + timedelta(weeks=step * interval)
            candidates = [monday + timedelta(days=d) for d in sorted(weekdays)]
        elif freq in ("MONTHLY", "YEARLY"):
            months = step * interval * (12 if freq == "YEARLY" else 1)
            year = wall.year + (wall.month - 1 + months) // 12
            month = (wall.month - 1 + months) % 12 + 1
            try:
                candidates = [wall.replace(year=year, month=month)]
            except ValueError:
                candidates = []  # e.g. the 31st in a short month
        else:
            return
        for candidate in candidates:
            if candidate < wall:
                continue
            compare = candidate if isinstance(first, datetime) else candidate.date()
            if limit is not None and compare > limit:
                return
            yield compare
            produced += 1
            if count is not None and produced >= count:
                return
        if candidates and candidates[0] > until + timedelta(days=1):
            return


def occurrences(event, first_day, last_day, display_zone):
    """Agenda entries (start, end, event) falling on days first_day..last_day inclusive."""
    found = []
    until = datetime.combine(last_day, time.max)
    length = event_length(event)
    zone = event.get("zone")
    for start in starts(event, until):
        wall_start = start if isinstance(start, datetime) else datetime.combine(start, time())
        if wall_start > until + timedelta(days=1):
            break
        if start in event["exdates"] or (isinstance(start, datetime)
                                         and start.date() in event["exdates"]):
            continue
        if isinstance(start, datetime):
            shown = (start.replace(tzinfo=zone).astimezone(display_zone).replace(tzinfo=None)
                     if zone else start)
            end = shown + length
            last = shown.date()
        else:
            shown, end = start, start + length
            last = end - timedelta(days=1) if length >= timedelta(days=1) else start
        first_shown = shown.date() if isinstance(shown, datetime) else shown
        if first_shown <= last_day and last >= first_day:
            found.append((shown, end, event))
    return found


def build_agenda(events, first_day, days, display_zone):
    """Return {day: [(sort key, text)]} for each day in the range."""
    last_day = first_day + timedelta(days=days - 1)
    agenda = {first_day + timedelta(days=i): [] for i in range(days)}
    for event in events:
        if (event.get("status") or "").upper() == "CANCELLED":
            continue
        for shown, end, _ in occurrences(event, first_day, last_day, display_zone):
            title = event.get("summary", "(no title)") + (
                f"  @ {event['location']}" if event.get("location") else "")
            if isinstance(shown, datetime):
                day, label = shown.date(), f"{shown:%H:%M}-{end:%H:%M}"
                if end == shown:
                    label = f"{shown:%H:%M}      "
                if end.date() != shown.date():
                    label = f"{shown:%H:%M}->{end:%d %b %H:%M}"
                agenda.get(day, []).append((1, shown, f"{label}  {title}"))
            else:
                span = max((end - shown).days, 1)
                for offset in range(span):
                    day = shown + timedelta(days=offset)
                    if day in agenda:
                        agenda[day].append((0, datetime.combine(day, time()),
                                            f"all day     {title}"))
    return {day: sorted(items, key=lambda i: (i[0], i[1], i[2])) for day, items in agenda.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print a daily agenda from an .ics file.")
    parser.add_argument("calendar", type=Path, help="the .ics file")
    parser.add_argument("--date", help="first day, YYYY-MM-DD (default: today)")
    parser.add_argument("--days", type=int, default=1, help="how many days to show (1)")
    parser.add_argument("--tz", default="UTC", help="time zone to show times in (UTC)")
    args = parser.parse_args(argv)
    if not 1 <= args.days <= 31:
        parser.error("--days must be between 1 and 31")
    if not args.calendar.is_file():
        parser.error(f"not a file: {args.calendar}")
    try:
        zone = ZoneInfo(args.tz)
        first = date.fromisoformat(args.date) if args.date else datetime.now(zone).date()
    except (ZoneInfoNotFoundError, ValueError) as err:
        parser.error(f"bad --tz or --date: {err}")

    events = parse_events(args.calendar.read_text(encoding="utf-8-sig", errors="replace"))
    if not events:
        print("No events found in that calendar.")
        return 1
    agenda = build_agenda(events, first, args.days, zone)
    for day, items in agenda.items():
        print(f"{day:%A %d %b %Y}")
        for _, _, text in items:
            print(f"  {text}")
        if not items:
            print("  Nothing scheduled.")
        print()
    total = sum(len(items) for items in agenda.values())
    print(f"{total} item(s) over {args.days} day(s), times in {args.tz}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
