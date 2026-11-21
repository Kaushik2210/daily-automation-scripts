"""Summarise application usage from an active-window log (time,app,title CSV)."""
import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

IDLE_APPS = {"lockapp", "loginwindow", "screensaverengine", "logonui"}


def read_rows(path):
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                rows.append((datetime.fromisoformat(row["time"]), row.get("app", ""),
                             row.get("title", "")))
            except (KeyError, ValueError):
                continue
    return sorted(rows, key=lambda r: r[0])


def durations(rows, idle_gap, ignore):
    """Yield (start, app, title, seconds): each row lasts until the next one, capped at idle_gap."""
    cap = idle_gap * 60
    for (start, app, title), following in zip(rows, rows[1:], strict=False):
        if app.lower() in ignore:
            continue
        seconds = min((following[0] - start).total_seconds(), cap)
        if seconds > 0:
            yield start, app or "(unknown)", title, seconds


def human(seconds):
    minutes = round(seconds / 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"


def summarise(entries, by_title=False):
    """Return {day: {label: seconds}} for (start, app, title, seconds) entries."""
    days = defaultdict(lambda: defaultdict(float))
    for start, app, title, seconds in entries:
        label = f"{app}: {title}" if by_title and title else app
        days[start.date().isoformat()][label] += seconds
    return days


def print_day(day, totals, top):
    total = sum(totals.values())
    print(f"{day}  total {human(total)}")
    for label, seconds in sorted(totals.items(), key=lambda item: -item[1])[:top]:
        share = 100 * seconds / total
        bar = "#" * max(1, round(share / 4))
        print(f"  {label[:34]:<34} {human(seconds):>7} {share:4.0f}%  {bar}")
    if len(totals) > top:
        print(f"  ... and {len(totals) - top} more")
    print()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report time spent per application.")
    parser.add_argument("log", type=Path, help="CSV from active-window-logger (time,app,title)")
    parser.add_argument("--date", help="only this day, YYYY-MM-DD")
    parser.add_argument("--top", type=int, default=8, help="applications per day (8)")
    parser.add_argument("--idle-gap", type=float, default=5,
                        help="longest gap in minutes to count as use; longer is idle (5)")
    parser.add_argument("--ignore", default="", help="extra apps to leave out, comma-separated")
    parser.add_argument("--by-title", action="store_true", help="split apps by window title")
    args = parser.parse_args(argv)
    if not args.log.is_file():
        parser.error(f"not a file: {args.log}")
    if args.date:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            parser.error("--date must look like 2026-11-21")

    ignore = IDLE_APPS | {a.strip().lower() for a in args.ignore.split(",") if a.strip()}
    rows = read_rows(args.log)
    entries = [e for e in durations(rows, args.idle_gap, ignore)
               if not args.date or e[0].date().isoformat() == args.date]
    if not entries:
        print("No usage found" + (f" for {args.date}" if args.date else "") + ".", file=sys.stderr)
        return 1
    days = summarise(entries, args.by_title)
    for day in sorted(days):
        print_day(day, days[day], args.top)
    if len(days) > 1:
        everything = defaultdict(float)
        for totals in days.values():
            for label, seconds in totals.items():
                everything[label] += seconds
        print_day(f"All {len(days)} days", everything, args.top)
    span = (rows[-1][0] - rows[0][0]).total_seconds() if rows else 0
    print(f"Based on {len(rows)} log row(s) covering {human(span)}; gaps over "
          f"{args.idle_gap:g} min and lock screens count as idle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
