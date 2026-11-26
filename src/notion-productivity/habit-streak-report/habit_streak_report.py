"""Report habit streaks and consistency from a habit-tracker JSON file."""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path


def load(path):
    """{habit: sorted unique dates} from {"habits": {name: ["YYYY-MM-DD", ...]}}."""
    data = json.loads(path.read_text(encoding="utf-8"))
    habits = data["habits"]
    if not isinstance(habits, dict):
        raise TypeError("'habits' must map each habit to a list of dates")
    return {name: sorted({date.fromisoformat(d) for d in days}) for name, days in habits.items()}


def streaks(days, today):
    """(current streak, best streak). The current streak survives until the end of today."""
    done = {d for d in days if d <= today}  # check-ins dated in the future don't count
    best = run = 0
    previous = None
    for day in sorted(done):
        run = run + 1 if previous and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    current, cursor = 0, today if today in done else today - timedelta(days=1)
    while cursor in done:
        current += 1
        cursor -= timedelta(days=1)
    return current, best


def report_for(name, days, today, window):
    done = set(days)
    start = today - timedelta(days=window - 1)
    in_window = sum(1 for d in done if start <= d <= today)
    current, best = streaks(days, today)
    past = [d for d in days if d <= today]
    return {"habit": name, "current": current, "best": best, "total": len(past),
            "window_done": in_window, "consistency": round(in_window / window * 100),
            "last_done": past[-1].isoformat() if past else None,
            "days_since": (today - past[-1]).days if past else None,
            "at_risk": current > 0 and today not in done,
            "recent": "".join("#" if today - timedelta(days=13 - i) in done else "-"
                              for i in range(14))}


def flags(item):
    if item["at_risk"]:
        return "do it today to keep the streak"
    if item["current"] == 0 and item["days_since"] is not None:
        return f"broken {item['days_since']} day(s) ago"
    if item["last_done"] is None:
        return "never done"
    return "done today" if item["days_since"] == 0 else ""


def render(items, today, window, markdown):
    if markdown:
        lines = [f"## Habit streaks ({today})", "",
                 f"| Habit | Streak | Best | Last {window} days | Total | Note |",
                 "|---|---|---|---|---|---|"]
        lines += [f"| {i['habit']} | {i['current']} | {i['best']} | {i['window_done']}/{window} "
                  f"({i['consistency']}%) | {i['total']} | {flags(i)} |" for i in items]
        return "\n".join(lines)
    width = max([len(i["habit"]) for i in items] + [5])
    lines = [f"Habit streaks as of {today}", "",
             f"{'':<{width}}  streak  best  last {window}d  last 14 days  note"]
    for i in items:
        lines.append(f"{i['habit']:<{width}}  {i['current']:>6}  {i['best']:>4}  "
                     f"{i['consistency']:>5}%     {i['recent']}  {flags(i)}".rstrip())
    done = sum(i["window_done"] for i in items)
    lines.append(f"\nOverall: {done} check-ins of {window * len(items)} possible "
                 f"({round(done / (window * len(items)) * 100)}%) in the last {window} days.")
    leader = max(items, key=lambda i: (i["current"], i["best"]))
    if leader["current"]:
        lines.append(f"Longest running streak: {leader['habit']} ({leader['current']} day(s)).")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Habit streaks and consistency report.")
    parser.add_argument("file", type=Path, help="habit-tracker JSON file")
    parser.add_argument("--today", help="treat this as today, YYYY-MM-DD")
    parser.add_argument("--window", type=int, default=30, help="days for consistency (30)")
    parser.add_argument("--habit", action="append", default=[], help="only this habit (repeatable)")
    parser.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    args = parser.parse_args(argv)
    if not 1 <= args.window <= 365:
        parser.error("--window must be between 1 and 365")
    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
    except ValueError:
        parser.error(f"--today must look like 2026-01-08, got '{args.today}'")
    try:
        habits = load(args.file)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as err:
        print(f"Can't read the habits: {err}", file=sys.stderr)
        return 1
    unknown = [h for h in args.habit if h not in habits]
    if unknown:
        print(f"No such habit: {', '.join(unknown)}. Known: {', '.join(habits) or 'none'}",
              file=sys.stderr)
        return 1
    items = [report_for(name, days, today, args.window) for name, days in habits.items()
             if not args.habit or name in args.habit]
    if not items:
        print("No habits to report on.", file=sys.stderr)
        return 1
    items.sort(key=lambda i: (-i["current"], -i["consistency"], i["habit"]))
    if args.format == "json":
        print(json.dumps({"today": today.isoformat(), "window": args.window, "habits": items},
                         indent=1))
    else:
        print(render(items, today, args.window, args.format == "markdown"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
