"""Explain cron expressions in plain English and show when they will run next."""
import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
MACROS = {"@yearly": "0 0 1 1 *", "@annually": "0 0 1 1 *", "@monthly": "0 0 1 * *",
          "@weekly": "0 0 * * 0", "@daily": "0 0 * * *", "@midnight": "0 0 * * *",
          "@hourly": "0 * * * *"}
RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]


def parse_field(text, index):
    """Return (sorted list of values, is_wildcard) for one cron field."""
    low, high = RANGES[index]
    names = {m[:3].lower(): i + 1 for i, m in enumerate(MONTHS)} if index == 3 else (
        {d[:3].lower(): i for i, d in enumerate(DAYS)} if index == 4 else {})
    values = set()
    for part in text.lower().split(","):
        base, _, step = part.partition("/")
        if step and (not step.isdigit() or int(step) < 1):
            raise ValueError(f"bad step in '{text}'")
        if base in ("*", "?"):
            start, end = low, high
        else:
            first, _, last = base.partition("-")
            start = names.get(first, int(first) if first.isdigit() else None)
            end = names.get(last, int(last) if last.isdigit() else None) if last else (
                high if step else start)
            if start is None or end is None:
                raise ValueError(f"can't read '{part}'")
        if not (low <= start <= high and low <= end <= high) or start > end:
            raise ValueError(f"'{part}' is outside {low}-{high}")
        values.update(range(start, end + 1, int(step or 1)))
    if index == 4:
        values = {v % 7 for v in values}
    return sorted(values), text in ("*", "?")


def clock(hour, minute):
    return f"{hour:02d}:{minute:02d}"


def join(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def runs_of(values):
    """[1,2,3,5] -> [(1, 3), (5, 5)]."""
    result = []
    for value in values:
        if result and value == result[-1][1] + 1:
            result[-1] = (result[-1][0], value)
        else:
            result.append((value, value))
    return result


def hour_span(hours):
    spans = runs_of(hours)
    if len(spans) == 1:
        return f"between {clock(hours[0], 0)} and {clock(hours[-1], 59)}"
    return "during hours " + join([str(h) for h in hours])


def describe_time(minutes, hours, minute_text, hour_text):
    if minute_text == "*" and hour_text == "*":
        return "every minute"
    if hour_text == "*":
        if minute_text.startswith("*/"):
            return f"every {minute_text[2:]} minutes"
        if len(minutes) == 1:
            return ("at the start of every hour" if minutes[0] == 0
                    else f"at minute {minutes[0]} of every hour")
        return "at minutes " + join([str(m) for m in minutes]) + " of every hour"
    if minute_text == "*":
        return "every minute " + hour_span(hours)
    if minute_text.startswith("*/"):
        return f"every {minute_text[2:]} minutes " + hour_span(hours)
    times = [clock(h, m) for h in hours for m in minutes]
    if len(times) <= 8:
        return "at " + join(times)
    return ("at minutes " + join([str(m) for m in minutes]) + " past hours "
            + join([str(h) for h in hours]))


def describe_days(dom, dow, month_values, dom_star, dow_star, month_star):
    parts = []
    if not dom_star:
        parts.append("on day " + join([str(d) for d in dom]) + " of the month")
    if not dow_star:
        spans = runs_of(dow)
        names = [DAYS[a] if a == b else f"{DAYS[a]} through {DAYS[b]}" if b - a > 1
                 else f"{DAYS[a]} and {DAYS[b]}" for a, b in spans]
        parts.append("on " + join(names))
    text = " or ".join(parts) if parts else "every day"
    if not month_star:
        spans = [MONTHS[a - 1] if a == b else f"{MONTHS[a - 1]} through {MONTHS[b - 1]}"
                 for a, b in runs_of(month_values)]
        text += " in " + join(spans)
    return text


def explain(expression):
    """Return (English description, parsed fields) for a 5-field expression or @macro."""
    expression = MACROS.get(expression.strip().lower(), expression.strip())
    if expression.lower() == "@reboot":
        return "once, when the system starts", None
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError(f"expected 5 fields (minute hour day month weekday), got {len(fields)}")
    parsed = [parse_field(f, i) for i, f in enumerate(fields)]
    (minutes, _), (hours, _), (dom, dom_star), (months, month_star), (dow, dow_star) = parsed
    when = describe_time(minutes, hours, fields[0], fields[1])
    days = describe_days(dom, dow, months, dom_star, dow_star, month_star)
    note = " (when both a day of the month and a weekday are given, either one matches)" if (
        not dom_star and not dow_star) else ""
    return f"{when[0].upper()}{when[1:]}, {days}{note}", parsed


def next_runs(parsed, start, count):
    """The next `count` run times strictly after `start` (a naive datetime)."""
    (minutes, _), (hours, _), (dom, dom_star), (months, _), (dow, dow_star) = parsed
    found, day = [], start.replace(hour=0, minute=0, second=0, microsecond=0)
    for _ in range(366 * 8):
        weekday = (day.weekday() + 1) % 7
        if day.month in months:
            in_dom, in_dow = day.day in dom, weekday in dow
            ok = (in_dom or in_dow) if not dom_star and not dow_star else (in_dom and in_dow)
            if ok:
                for hour in hours:
                    for minute in minutes:
                        moment = day.replace(hour=hour, minute=minute)
                        if moment > start:
                            found.append(moment)
        if len(found) >= count:
            break
        day += timedelta(days=1)
    return found[:count]


def cron_lines(path):
    """Yield (expression, command) for each schedule in a crontab file."""
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or re.match(r"^[A-Za-z_]+\s*=", line):
            continue
        if line.startswith("@"):
            head, _, command = line.partition(" ")
            yield head, command.strip()
        else:
            fields = line.split(None, 5)
            yield " ".join(fields[:5]), fields[5] if len(fields) > 5 else ""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Explain cron expressions in plain English.")
    parser.add_argument("expressions", nargs="*", help="e.g. '*/15 9-17 * * 1-5' or @daily")
    parser.add_argument("--file", type=Path, help="explain every line of a crontab file")
    parser.add_argument("--next", type=int, default=3, help="how many future runs to show (3)")
    parser.add_argument("--from", dest="start", help="start time YYYY-MM-DD HH:MM (default: now)")
    args = parser.parse_args(argv)
    if not args.expressions and not args.file:
        parser.error("give a cron expression in quotes, or --file CRONTAB")
    try:
        start = datetime.strptime(args.start, "%Y-%m-%d %H:%M") if args.start else (
            datetime.now().replace(second=0, microsecond=0))
    except ValueError:
        parser.error("--from must look like '2026-11-18 09:30'")

    jobs = [(e, "") for e in args.expressions]
    if args.file:
        if not args.file.is_file():
            parser.error(f"not a file: {args.file}")
        jobs += list(cron_lines(args.file))
    bad = 0
    for expression, command in jobs:
        print(f"{expression}" + (f"   {command}" if command else ""))
        try:
            text, parsed = explain(expression)
        except ValueError as err:
            print(f"  ! {err}\n")
            bad += 1
            continue
        print(f"  {text}")
        if parsed and args.next > 0:
            runs = next_runs(parsed, start, args.next)
            print("  next: " + ("; ".join(f"{r:%a %d %b %Y %H:%M}" for r in runs)
                                if runs else "never (no matching date within 8 years)"))
        print()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
