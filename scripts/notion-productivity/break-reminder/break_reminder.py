"""Nag you to take a break every N minutes, right in the terminal. No desktop app needed."""
import argparse
import sys
import time
from datetime import datetime, timedelta

DEFAULT_MESSAGES = [
    "Stand up and stretch your legs.",
    "Drink some water.",
    "Look at something 20 feet away for 20 seconds.",
    "Roll your shoulders and unclench your jaw.",
    "Take a few slow, deep breaths.",
]


def reminder_times(start, every_minutes, total_minutes):
    """Datetimes of each reminder, starting `every_minutes` after `start`."""
    count = total_minutes // every_minutes
    return [start + timedelta(minutes=every_minutes * i) for i in range(1, count + 1)]


def pick_message(index, custom=None):
    """A custom message is repeated; otherwise the built-in ones rotate."""
    return custom or DEFAULT_MESSAGES[index % len(DEFAULT_MESSAGES)]


def parse_start(text):
    if not text:
        return datetime.now().replace(microsecond=0)
    hour, minute = (int(part) for part in text.split(":"))
    return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Remind yourself to take breaks.")
    parser.add_argument("--every", type=int, default=30, help="minutes between reminders (30)")
    parser.add_argument("--total", type=int, default=240, help="minutes to keep going (240)")
    parser.add_argument("--message", help="your own reminder text (default: rotating tips)")
    parser.add_argument("--unit", choices=["minutes", "seconds"], default="minutes",
                        help="read --every as minutes or seconds (seconds suits a demo)")
    parser.add_argument("--plan", action="store_true", help="only list the reminder times")
    parser.add_argument("--start", help="clock time the session starts, HH:MM (default: now)")
    parser.add_argument("--no-bell", action="store_true", help="no sound with each reminder")
    args = parser.parse_args(argv)
    if args.every < 1 or args.total < args.every:
        parser.error("--every must be at least 1 and no larger than --total")
    try:
        start = parse_start(args.start)
    except ValueError:
        parser.error("--start must look like 09:30")

    times = reminder_times(start, args.every, args.total)
    if args.plan:
        for i, moment in enumerate(times):
            print(f"{moment:%H:%M}  {pick_message(i, args.message)}")
        print(f"{len(times)} reminder(s) over {args.total} minutes, every {args.every} minutes.")
        return 0
    wait = args.every * (1 if args.unit == "seconds" else 60)
    print(f"Reminding you every {args.every} {args.unit}. Press Ctrl+C to stop.")
    try:
        for i in range(len(times)):
            time.sleep(wait)
            print(f"[{datetime.now():%H:%M:%S}] {pick_message(i, args.message)}"
                  + ("" if args.no_bell else "\a"))
    except KeyboardInterrupt:
        print("\nStopped. Take care of yourself!")
        return 130
    print("Session finished. Great job.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
