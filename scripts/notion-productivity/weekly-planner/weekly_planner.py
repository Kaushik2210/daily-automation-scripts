"""Generate a weekly planner in markdown: goals, a section per day and a review."""
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path


def next_monday(today):
    """The coming Monday (today if it already is Monday)."""
    return today + timedelta(days=(7 - today.weekday()) % 7)


def monday_of(day):
    return day - timedelta(days=day.weekday())


def build_planner(week_start, goals=(), weekend=False, slots=3):
    """Return the planner as markdown text for the week starting on `week_start`."""
    last = week_start + timedelta(days=6 if weekend else 4)
    lines = [f"# Week of {week_start:%d %b %Y}", f"*{week_start:%d %b} to {last:%d %b}*", ""]
    lines.append("## Goals")
    lines += [f"- [ ] {goal}" for goal in goals] or ["- [ ] "]
    lines.append("")
    for offset in range((last - week_start).days + 1):
        day = week_start + timedelta(days=offset)
        lines.append(f"## {day:%A %d %b}")
        lines += ["- [ ] "] * slots
        lines.append("")
    lines += ["## Review", "- What went well:", "- What to change next week:", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a weekly planner in markdown.")
    parser.add_argument("--week-of", help="any date in the week, YYYY-MM-DD (default: next Monday)")
    parser.add_argument("--goals", nargs="+", default=[], help="weekly goals, one per argument")
    parser.add_argument("--weekend", action="store_true", help="include Saturday and Sunday")
    parser.add_argument("--slots", type=int, default=3, help="to-do lines per day (3)")
    parser.add_argument("-o", "--output", type=Path, help="write the planner to this file")
    parser.add_argument("--apply", action="store_true",
                        help="really write --output (default only prints the planner)")
    args = parser.parse_args(argv)
    if args.slots < 1:
        parser.error("--slots must be at least 1")
    try:
        week = monday_of(date.fromisoformat(args.week_of)) if args.week_of \
            else next_monday(date.today())
    except ValueError:
        parser.error("--week-of must look like 2026-01-05")

    text = build_planner(week, args.goals, args.weekend, args.slots)
    if args.output and args.apply:
        if args.output.exists():
            print(f"{args.output} already exists; choose another name.", file=sys.stderr)
            return 1
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}.")
        return 0
    print(text)
    if args.output:
        print(f"(preview only: use --apply to write {args.output})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
