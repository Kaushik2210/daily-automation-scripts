"""Summarise hours by project, task, day or week from a CSV time log."""
import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

MAX_ENTRY_MINUTES = 16 * 60  # longer than this is almost certainly a typo


def parse_clock(text):
    return datetime.strptime(text.strip(), "%H:%M")


def entry_minutes(row):
    """Minutes for one log row: an `hours` value, or the gap between `start` and `end`."""
    if (row.get("hours") or "").strip():
        minutes = round(float(row["hours"]) * 60)
    else:
        start, end = parse_clock(row["start"]), parse_clock(row["end"])
        minutes = round((end - start).total_seconds() / 60)
        if minutes < 0:  # worked past midnight
            minutes += 24 * 60
    if minutes <= 0:
        raise ValueError("zero or negative time")
    if minutes > MAX_ENTRY_MINUTES:
        raise ValueError(f"{minutes / 60:.1f} hours in one entry; check the start and end times")
    return minutes


def read_log(path, round_to):
    """Return (entries, problems). An entry is {date, project, task, minutes}."""
    entries, problems = [], []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        names = {n.strip().lower() for n in (reader.fieldnames or [])}
        if not {"date", "project"} <= names or not ("hours" in names or {"start", "end"} <= names):
            raise ValueError("the log needs columns date, project and either hours or start,end")
        for number, raw in enumerate(reader, 2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
            try:
                minutes = entry_minutes(row)
                if round_to:
                    minutes = math.ceil(minutes / round_to) * round_to
                entries.append({"date": date.fromisoformat(row["date"]), "project": row["project"],
                                "task": row.get("task", ""), "minutes": minutes})
            except (ValueError, KeyError) as err:
                problems.append(f"line {number}: {err}")
    return entries, problems


def parse_rates(items):
    """['50', 'website=80'] -> (default 50.0, {'website': 80.0})."""
    default, per_project = None, {}
    for item in items:
        name, sep, value = item.rpartition("=")
        try:
            rate = float(value)
        except ValueError:
            raise ValueError(f"bad rate '{item}' (use 50 or project=50)") from None
        if sep:
            per_project[name] = rate
        else:
            default = rate
    return default, per_project


def key_for(entry, group_by):
    day = entry["date"]
    if group_by == "day":
        return day.isoformat()
    if group_by == "week":
        year, week, _ = day.isocalendar()
        return f"{year}-W{week:02d}"
    if group_by == "task":
        return f"{entry['project']} / {entry['task'] or '(no task)'}"
    return entry["project"]


def summarise(entries, group_by, default_rate, rates):
    groups = defaultdict(lambda: {"minutes": 0, "amount": 0.0})
    for entry in entries:
        group = groups[key_for(entry, group_by)]
        group["minutes"] += entry["minutes"]
        rate = rates.get(entry["project"], default_rate)
        if rate is not None:
            group["amount"] += entry["minutes"] / 60 * rate
    ordered = sorted(groups.items(),
                     key=lambda kv: (kv[0] if group_by in ("day", "week") else (-kv[1]["minutes"],
                                                                                 kv[0])))
    return ordered


def hours(minutes):
    return f"{minutes / 60:.2f}"


def render(rows, entries, days, billing, fmt):
    total = sum(g["minutes"] for _, g in rows)
    amount = sum(g["amount"] for _, g in rows)
    if fmt == "json":
        return json.dumps({"total_hours": round(total / 60, 2), "days_worked": days,
                           "groups": [{"name": n, "hours": round(g["minutes"] / 60, 2),
                                       "share": round(g["minutes"] / total * 100, 1),
                                       **({"amount": round(g["amount"], 2)} if billing else {})}
                                      for n, g in rows]}, indent=1)
    if fmt == "csv":
        lines = ["name,hours,share_percent" + (",amount" if billing else "")]
        for name, g in rows:
            lines.append(f'"{name}",{hours(g["minutes"])},{g["minutes"] / total * 100:.1f}'
                         + (f',{g["amount"]:.2f}' if billing else ""))
        return "\n".join(lines)
    width = max([len(n) for n, _ in rows] + [5])
    if fmt == "markdown":
        head = "| Name | Hours | Share |" + (" Amount |" if billing else "")
        lines = [head, "|---|---|---|" + ("---|" if billing else "")]
        for name, g in rows:
            lines.append(f"| {name} | {hours(g['minutes'])} | {g['minutes'] / total * 100:.0f}% |"
                         + (f" {g['amount']:,.2f} |" if billing else ""))
        lines.append(f"| **Total** | {hours(total)} | 100% |" + (f" {amount:,.2f} |" if billing
                                                                  else ""))
        return "\n".join(lines)
    lines = [f"{'':<{width}}  {'hours':>7}  {'share':>5}"
             + (f"  {'amount':>10}" if billing else "")]
    for name, g in rows:
        share = g["minutes"] / total * 100
        lines.append(f"{name:<{width}}  {hours(g['minutes']):>7}  {share:>4.0f}%"
                     + (f"  {g['amount']:>10,.2f}" if billing else "")
                     + f"  {'#' * max(1, round(share / 5))}")
    lines.append(f"{'Total':<{width}}  {hours(total):>7}" + " " * 7
                 + (f"  {amount:>10,.2f}" if billing else ""))
    lines.append(f"\n{len(entries)} entries over {days} day(s), "
                 f"about {total / 60 / days:.2f} h per active day.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Hours by project from a CSV time log.")
    parser.add_argument("log", type=Path, help="CSV with date, project, [task], hours or start,end")
    parser.add_argument("--group-by", choices=["project", "task", "day", "week"], default="project")
    parser.add_argument("--from", dest="start", help="first day to include, YYYY-MM-DD")
    parser.add_argument("--to", dest="end", help="last day to include, YYYY-MM-DD")
    parser.add_argument("--project", action="append", default=[], help="only this project")
    parser.add_argument("--round", type=int, default=0, metavar="MINUTES",
                        help="round every entry up to a multiple of this, e.g. 15")
    parser.add_argument("--rate", action="append", default=[], metavar="[PROJECT=]RATE",
                        help="hourly rate, overall or per project (repeatable)")
    parser.add_argument("--format", choices=["text", "markdown", "json", "csv"], default="text")
    args = parser.parse_args(argv)
    if args.round < 0:
        parser.error("--round can't be negative")
    try:
        start = date.fromisoformat(args.start) if args.start else None
        end = date.fromisoformat(args.end) if args.end else None
        default_rate, rates = parse_rates(args.rate)
    except ValueError as err:
        parser.error(str(err))
    try:
        entries, problems = read_log(args.log, args.round)
    except (OSError, ValueError, UnicodeDecodeError) as err:
        print(f"Can't read the log: {err}", file=sys.stderr)
        return 1
    entries = [e for e in entries
               if (not start or e["date"] >= start) and (not end or e["date"] <= end)
               and (not args.project or e["project"] in args.project)]
    for problem in problems[:5]:
        print(f"Skipped {problem}", file=sys.stderr)
    if len(problems) > 5:
        print(f"...and {len(problems) - 5} more skipped line(s).", file=sys.stderr)
    if not entries:
        print("No time entries match.", file=sys.stderr)
        return 1
    billing = default_rate is not None or bool(rates)
    rows = summarise(entries, args.group_by, default_rate, rates)
    days = len({e["date"] for e in entries})
    print(render(rows, entries, days, billing, args.format))
    return 0


if __name__ == "__main__":
    sys.exit(main())
