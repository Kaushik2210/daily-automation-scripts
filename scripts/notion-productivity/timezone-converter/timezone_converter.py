"""Convert a time between time zones, handling daylight saving time correctly."""
import argparse
import contextlib
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

with contextlib.suppress(ImportError):
    import tzdata  # noqa: F401  (supplies the zone database on Windows)


def parse_clock(text):
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M%p", "%I%p"):
        try:
            return datetime.strptime(text.strip().upper().replace(" ", ""), fmt).time()
        except ValueError:
            continue
    raise ValueError(f"can't read the time '{text}': try 14:30 or 2:30pm")


def convert(when, source, targets):
    """Return [(zone_name, converted_datetime)] for a naive `when` in the `source` zone."""
    start = when.replace(tzinfo=ZoneInfo(source))
    return [(name, start.astimezone(ZoneInfo(name))) for name in targets]


def day_note(original, converted):
    delta = (converted.date() - original.date()).days
    return {0: "", 1: " (+1 day)", -1: " (-1 day)"}.get(delta, f" ({delta:+d} days)")


def find_zones(text):
    needle = text.lower().replace(" ", "_")
    return sorted(z for z in available_timezones() if needle in z.lower())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert a time between time zones.")
    parser.add_argument("time", nargs="?", help="time to convert, e.g. 14:30 or 2:30pm")
    parser.add_argument("--from", dest="source", default="UTC", help="source zone (default UTC)")
    parser.add_argument("--to", nargs="+", default=["UTC"], help="one or more target zones")
    parser.add_argument("--date", help="date for the conversion, YYYY-MM-DD (default: today)")
    parser.add_argument("--find", metavar="TEXT", help="search zone names instead, e.g. london")
    args = parser.parse_args(argv)

    if args.find:
        zones = find_zones(args.find)
        print("\n".join(zones) if zones else "No zone names match.")
        return 0 if zones else 1
    if not args.time:
        parser.error("give a time to convert, or use --find to look up zone names")
    try:
        day = date.fromisoformat(args.date) if args.date else date.today()
        when = datetime.combine(day, parse_clock(args.time))
        results = convert(when, args.source, args.to)
    except ValueError as err:
        parser.error(str(err))
    except ZoneInfoNotFoundError as err:
        parser.error(f"unknown time zone {err}. Try --find to search names.")

    origin = when.replace(tzinfo=ZoneInfo(args.source))
    print(f"{origin:%a %Y-%m-%d %H:%M} {args.source} ({origin:%z})")
    for name, converted in results:
        note = day_note(origin, converted)
        print(f"  {converted:%a %Y-%m-%d %H:%M}  {name} ({converted:%z}){note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
