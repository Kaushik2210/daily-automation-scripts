"""Count down to a date, a clock time or a duration like 90s, 25m or 1h30m."""
import argparse
import re
import sys
import time
from datetime import datetime, timedelta

DURATION = re.compile(r"(\d+)\s*([dhms])", re.IGNORECASE)
UNITS = {"d": "days", "h": "hours", "m": "minutes", "s": "seconds"}


def parse_target(text, now):
    """Return the target datetime: a duration from now, or an absolute date/time."""
    text = text.strip()
    parts = DURATION.findall(text)
    if parts and "".join(f"{n}{u}" for n, u in parts) == re.sub(r"\s+", "", text):
        return now + timedelta(**{UNITS[u.lower()]: int(n) for n, u in parts})
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"can't read '{text}': use 2026-12-25, '2026-12-25 18:00' or 1h30m")


def describe(delta):
    """'3 days, 4 hours, 5 minutes, 6 seconds' for a timedelta (absolute value)."""
    total = int(abs(delta.total_seconds()))
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, seconds = divmod(rest, 60)
    parts = [(days, "day"), (hours, "hour"), (minutes, "minute"), (seconds, "second")]
    shown = [f"{n} {name}{'' if n == 1 else 's'}" for n, name in parts if n]
    return ", ".join(shown) if shown else "0 seconds"


def message(target, now):
    delta = target - now
    if delta.total_seconds() >= 0:
        return f"{describe(delta)} until {target:%Y-%m-%d %H:%M:%S}"
    return f"{target:%Y-%m-%d %H:%M:%S} was {describe(delta)} ago"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Count down to a date or duration.")
    parser.add_argument("target", help="2026-12-25, '2026-12-25 18:00', or a duration like 1h30m")
    parser.add_argument("--now", help="pretend it is this moment, e.g. '2026-01-01 09:00'")
    parser.add_argument("--live", action="store_true", help="keep updating every second")
    args = parser.parse_args(argv)

    try:
        now = parse_target(args.now, datetime.now()) if args.now else datetime.now()
        target = parse_target(args.target, now)
    except ValueError as err:
        parser.error(str(err))

    if not args.live:
        print(message(target, now))
        return 0
    try:
        while target > datetime.now():
            sys.stdout.write(f"\r{message(target, datetime.now()):<60}")
            sys.stdout.flush()
            time.sleep(1)
        print("\nTime's up!")
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
