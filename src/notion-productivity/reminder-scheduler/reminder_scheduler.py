"""Schedule one-off terminal reminders: '25m', '15:30', or a list of them from a file."""
import argparse
import platform
import re
import shutil
import subprocess  # web-ok: only used by --notify; plans and terminal reminders work anywhere
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

DURATION = re.compile(r"(\d+(?:\.\d+)?)\s*(h|m|s)", re.IGNORECASE)


def parse_when(text, now):
    """'+25m', '1h30m', '90s', '15:30' or '2026-11-22 09:00' -> a datetime after `now`."""
    text = text.strip().lower().removeprefix("in ").strip().lstrip("+")
    if re.fullmatch(r"(?:\d+(?:\.\d+)?\s*[hms]\s*)+", text):
        seconds = sum(float(n) * {"h": 3600, "m": 60, "s": 1}[u.lower()]
                      for n, u in DURATION.findall(text))
        if seconds <= 0:
            raise ValueError(f"'{text}' is not a future time")
        return now + timedelta(seconds=seconds)
    clock = re.fullmatch(r"(\d{1,2}):(\d{2})", text)
    if clock:
        hour, minute = int(clock.group(1)), int(clock.group(2))
        if hour > 23 or minute > 59:
            raise ValueError(f"'{text}' is not a valid time")
        moment = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return moment if moment > now else moment + timedelta(days=1)
    for pattern in ("%Y-%m-%d %H:%M", "%Y-%m-%dt%H:%M"):
        try:
            moment = datetime.strptime(text, pattern)
        except ValueError:
            continue
        if moment <= now:
            raise ValueError(f"{moment:%Y-%m-%d %H:%M} is already in the past")
        return moment
    raise ValueError(f"can't understand the time '{text}' (try 25m, 1h30m, 15:30)")


def read_file(path, now):
    """Lines like '+25m message' or '15:30 message'. Return [(datetime, message)]."""
    reminders = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        when, _, message = line.partition(" ")
        if when.lower() == "in":
            when, _, message = message.strip().partition(" ")
        try:
            reminders.append((parse_when(when, now), message.strip() or "Reminder"))
        except ValueError as err:
            raise ValueError(f"line {number}: {err}") from None
    return reminders


def notify(message):
    """Best-effort desktop notification."""
    system = platform.system()
    if system == "Darwin":
        script = f'display notification "{message}" with title "Reminder"'
        subprocess.run(["osascript", "-e", script], check=False, timeout=10)
    elif system == "Linux" and shutil.which("notify-send"):
        subprocess.run(["notify-send", "Reminder", message], check=False, timeout=10)
    elif system == "Windows" and shutil.which("msg"):
        subprocess.run(["msg", "*", "/TIME:30", message], check=False, timeout=10)


def run(reminders, now=datetime.now, sleep=time.sleep, out=print, desktop=False):
    """Wait for each reminder in time order and fire it."""
    for moment, message in sorted(reminders):
        while True:
            remaining = (moment - now()).total_seconds()
            if remaining <= 0:
                break
            sleep(min(remaining, 1.0))
        out(f"\a[{moment:%H:%M:%S}] REMINDER: {message}")
        if desktop:
            notify(message)
    return len(reminders)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Schedule one-off reminders in the terminal.")
    parser.add_argument("when", nargs="?", help="25m, 1h30m, 90s, 15:30 or '2026-11-22 09:00'")
    parser.add_argument("message", nargs="*", help="what to remind you of")
    parser.add_argument("--file", type=Path, help="read 'when message' lines from a file")
    parser.add_argument("--plan", action="store_true", help="show the schedule without waiting")
    parser.add_argument("--now", help="pretend it is this time, 'YYYY-MM-DD HH:MM' (for planning)")
    parser.add_argument("--notify", action="store_true", help="also show a desktop notification")
    args = parser.parse_args(argv)
    if not args.when and not args.file:
        parser.error("give a time and message (e.g. 25m 'Stand up') or --file FILE")
    try:
        current = datetime.strptime(args.now, "%Y-%m-%d %H:%M") if args.now else datetime.now()
    except ValueError:
        parser.error("--now must look like '2026-11-21 09:00'")

    try:
        reminders = []
        if args.when:
            reminders.append((parse_when(args.when, current), " ".join(args.message) or "Reminder"))
        if args.file:
            reminders += read_file(args.file, current)
    except (ValueError, OSError) as err:
        print(f"Can't schedule that: {err}", file=sys.stderr)
        return 1
    print(f"{len(reminders)} reminder(s), starting {current:%Y-%m-%d %H:%M:%S}:")
    for moment, message in sorted(reminders):
        wait = int((moment - current).total_seconds())
        eta = f"{wait // 3600}h {wait % 3600 // 60:02d}m"
        print(f"  {moment:%a %d %b %H:%M}  (in {eta})  {message}")
    if args.plan:
        print("Plan only; run without --plan to wait for them.")
        return 0
    print("\nWaiting... leave this window open (Ctrl-C to cancel).")
    try:
        fired = run(reminders, desktop=args.notify)
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 0
    print(f"Done: {fired} reminder(s) shown.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
