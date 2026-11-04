"""Run focus and break cycles with a terminal countdown (the Pomodoro technique)."""
import argparse
import sys
import time
from datetime import datetime, timedelta


def build_schedule(focus=25, short_break=5, long_break=15, sessions=4, rounds=1):
    """Return [(label, minutes)]: focus/short-break pairs, then a long break, per round."""
    schedule = []
    for _ in range(rounds):
        for session in range(1, sessions + 1):
            schedule.append((f"Focus {session}/{sessions}", focus))
            if session == sessions:
                schedule.append(("Long break", long_break))
            else:
                schedule.append(("Short break", short_break))
    return schedule


def clock_plan(schedule, start):
    """Return [(start_time_text, label, minutes)] beginning at the datetime `start`."""
    rows, moment = [], start
    for label, minutes in schedule:
        rows.append((moment.strftime("%H:%M"), label, minutes))
        moment += timedelta(minutes=minutes)
    return rows, moment


def format_remaining(seconds):
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def countdown(label, total_seconds, bell=True, out=sys.stdout):
    for left in range(total_seconds, 0, -1):
        out.write(f"\r{label:<14} {format_remaining(left)} ")
        out.flush()
        time.sleep(1)
    out.write(f"\r{label:<14} done!      \n")
    if bell:
        out.write("\a")
    out.flush()


def parse_start(text):
    hour, minute = (int(part) for part in text.split(":"))
    return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pomodoro focus/break timer.")
    parser.add_argument("--focus", type=int, default=25, help="focus minutes (25)")
    parser.add_argument("--break", dest="short_break", type=int, default=5, help="short break (5)")
    parser.add_argument("--long-break", type=int, default=15, help="long break minutes (15)")
    parser.add_argument("--sessions", type=int, default=4, help="focus sessions per long break (4)")
    parser.add_argument("--rounds", type=int, default=1, help="how many full rounds (1)")
    parser.add_argument("--unit", choices=["minutes", "seconds"], default="minutes",
                        help="read the numbers as minutes or seconds (seconds suits a demo)")
    parser.add_argument("--plan", action="store_true", help="only print the schedule, don't wait")
    parser.add_argument("--start", default="09:00", help="clock time the plan starts at (09:00)")
    parser.add_argument("--no-bell", action="store_true", help="no sound at the end of a phase")
    args = parser.parse_args(argv)
    if min(args.focus, args.short_break, args.long_break, args.sessions, args.rounds) < 1:
        parser.error("all durations and counts must be at least 1")
    try:
        start = parse_start(args.start)
    except ValueError:
        parser.error("--start must look like 09:30")

    schedule = build_schedule(args.focus, args.short_break, args.long_break,
                              args.sessions, args.rounds)
    scale = 1 if args.unit == "seconds" else 60
    if args.plan:
        rows, end = clock_plan(schedule, start)
        for when, label, minutes in rows:
            print(f"{when}  {label:<12} {minutes} min")
        focus_total = sum(m for label, m in schedule if label.startswith("Focus"))
        print(f"Ends at {end:%H:%M}. {focus_total} minutes of focus in {len(schedule)} phases.")
        return 0
    try:
        for label, minutes in schedule:
            countdown(label, minutes * scale, bell=not args.no_bell)
    except KeyboardInterrupt:
        print("\nStopped. Nice work so far!")
        return 130
    print("All rounds complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
