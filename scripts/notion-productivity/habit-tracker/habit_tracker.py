"""Track daily habits and streaks from the terminal. Data lives in a small JSON file."""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

DEFAULT_FILE = Path.home() / ".habits.json"


def load(path):
    if not path.exists():
        return {"habits": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def streaks(dates, today):
    """Return (current_streak, best_streak) for a list of ISO date strings.

    The current streak survives until the end of today: checking in yesterday still counts.
    """
    days = sorted({date.fromisoformat(d) for d in dates})
    best = run = 0
    previous = None
    for day in days:
        run = run + 1 if previous and (day - previous).days == 1 else 1
        best = max(best, run)
        previous = day
    current = 0
    cursor = today if today in days else today - timedelta(days=1)
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)
    return current, best


def grid(dates, today, length=14):
    """A short history like '##.#...' ending today ('#' done, '.' missed)."""
    done = set(dates)
    return "".join("#" if (today - timedelta(days=i)).isoformat() in done else "."
                   for i in range(length - 1, -1, -1))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Track daily habits and streaks.")
    parser.add_argument("action", choices=["check", "uncheck", "list", "report"],
                        help="check/uncheck a habit for a day, list habits, or show a report")
    parser.add_argument("name", nargs="?", help="habit name (for check and uncheck)")
    parser.add_argument("--date", help="day to check, YYYY-MM-DD (default: today)")
    parser.add_argument("--today", help="pretend today is this date (handy for testing)")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE,
                        help=f"data file (default: {DEFAULT_FILE})")
    args = parser.parse_args(argv)

    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
        day = date.fromisoformat(args.date) if args.date else today
    except ValueError:
        parser.error("dates must look like 2026-01-31")
    data = load(args.file)
    habits = data["habits"]

    if args.action in ("check", "uncheck"):
        if not args.name:
            parser.error(f"{args.action} needs a habit name")
        dates = set(habits.get(args.name, []))
        (dates.add if args.action == "check" else dates.discard)(day.isoformat())
        habits[args.name] = sorted(dates)
        save(args.file, data)
        current, _ = streaks(habits[args.name], today)
        print(f"{args.action}ed '{args.name}' for {day}. Current streak: {current} day(s).")
        return 0

    if not habits:
        print("No habits yet. Add one with: check NAME")
        return 0
    if args.action == "list":
        print("\n".join(sorted(habits)))
        return 0
    print(f"{'habit':<14}{'streak':>7}{'best':>6}{'total':>7}  last 14 days (to {today})")
    for name in sorted(habits):
        current, best = streaks(habits[name], today)
        print(f"{name:<14}{current:>7}{best:>6}{len(habits[name]):>7}  {grid(habits[name], today)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
