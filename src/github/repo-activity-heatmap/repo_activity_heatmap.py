"""Draw a GitHub-style commit heatmap (text or SVG) from a repository or a list of dates."""
import argparse
import json
import re
import subprocess  # web-ok: git only runs without --from-file; saved date lists work anywhere
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
STYLES = {"ascii": " .:+#", "unicode": " ░▒▓█"}
COLOURS = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]


def parse_dates(text):
    """Every YYYY-MM-DD found at the start of a line (extra time text is ignored)."""
    found = []
    for line in text.splitlines():
        match = re.match(r"\s*(\d{4}-\d{2}-\d{2})", line)
        if match:
            try:
                found.append(date.fromisoformat(match.group(1)))
            except ValueError:
                continue
    return found


def git_dates(repo, author, since):
    command = ["git", "-C", str(repo), "log", "--all", "--format=%ad", "--date=short"]
    if author:
        command.append(f"--author={author}")
    if since:
        command.append(f"--since={since}")
    result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode:
        raise OSError((result.stderr.strip().splitlines() or ["git log failed"])[-1])
    return parse_dates(result.stdout)


def level(count, biggest):
    """0 for no activity, else 1-4 scaled to the busiest day."""
    return 0 if not count else max(1, -(-4 * count // biggest))


def week_grid(counts, end, weeks):
    """Columns of 7 days (Mon..Sun), the last column holding `end`. None marks future days."""
    monday = end - timedelta(days=end.weekday()) - timedelta(weeks=weeks - 1)
    return [[(monday + timedelta(weeks=w, days=d)) for d in range(7)] for w in range(weeks)], monday


def streaks(days, end):
    """(longest run of consecutive active days, run that is still going at `end`)."""
    longest = run = 0
    previous = None
    for day in sorted(days):
        run = run + 1 if previous and day - previous == timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day
    current, cursor = 0, end if end in days else end - timedelta(days=1)
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)
    return longest, current


def render_text(counts, end, weeks, glyphs):
    columns, _ = week_grid(counts, end, weeks)
    biggest = max(counts.values(), default=0)
    header, last_month = "     ", None
    for column in columns:
        month = column[0].strftime("%b")
        header += month[0] if month != last_month else " "
        last_month = month
    lines = [header.rstrip()]
    for row, name in enumerate(DAYS):
        cells = ""
        for column in columns:
            day = column[row]
            cells += "?" if day > end else glyphs[level(counts.get(day, 0), biggest)]
        lines.append(f"{name}  {cells}".rstrip())
    return "\n".join(lines).replace("?", " ")


def render_svg(counts, end, weeks):
    columns, _ = week_grid(counts, end, weeks)
    biggest = max(counts.values(), default=0)
    size, gap = 12, 3
    width, height = weeks * (size + gap) + 30, 7 * (size + gap) + 10
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'role="img" aria-label="Commit activity for {weeks} weeks">']
    for x, column in enumerate(columns):
        for y, day in enumerate(column):
            if day > end:
                continue
            count = counts.get(day, 0)
            out.append(f'<rect x="{30 + x * (size + gap)}" y="{5 + y * (size + gap)}" '
                       f'width="{size}" height="{size}" rx="2" '
                       f'fill="{COLOURS[level(count, biggest)]}">'
                       f"<title>{day.isoformat()}: {count} commit(s)</title></rect>")
    out.append("</svg>")
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Commit activity heatmap.")
    parser.add_argument("--repo", type=Path, default=Path("."), help="the repository (.)")
    parser.add_argument("--from-file", type=Path, dest="source",
                        help="a text file with one commit date (YYYY-MM-DD) per line")
    parser.add_argument("--author", help="only commits by this author (name or email)")
    parser.add_argument("--since", help="git date filter, e.g. '1 year ago'")
    parser.add_argument("--weeks", type=int, default=26, help="weeks to draw (26)")
    parser.add_argument("--end", help="last day to show, YYYY-MM-DD (today)")
    parser.add_argument("--style", choices=sorted(STYLES), default="ascii")
    parser.add_argument("--format", choices=["text", "json", "svg"], default="text")
    args = parser.parse_args(argv)
    if not 1 <= args.weeks <= 104:
        parser.error("--weeks must be between 1 and 104")
    try:
        end = date.fromisoformat(args.end) if args.end else date.today()
    except ValueError:
        parser.error(f"--end must look like 2026-11-25, got '{args.end}'")
    try:
        dates = (parse_dates(args.source.read_text(encoding="utf-8")) if args.source
                 else git_dates(args.repo, args.author, args.since))
    except (OSError, subprocess.SubprocessError) as err:
        print(f"Can't read the commit dates: {err}", file=sys.stderr)
        return 1

    _, first = week_grid({}, end, args.weeks)
    counts = Counter(d for d in dates if first <= d <= end)
    active = set(counts)
    longest, current = streaks(active, end)
    weekday = Counter()
    for day, n in counts.items():
        weekday[day.weekday()] += n
    busiest = max(counts.items(), key=lambda kv: (kv[1], kv[0]), default=None)
    summary = {"from": first.isoformat(), "to": end.isoformat(), "commits": sum(counts.values()),
               "active_days": len(active), "longest_streak": longest, "current_streak": current,
               "busiest_day": ({"date": busiest[0].isoformat(), "commits": busiest[1]}
                               if busiest else None),
               "busiest_weekday": DAYS[max(weekday, key=lambda k: (weekday[k], -k))]
               if weekday else None}
    if args.format == "svg":
        print(render_svg(counts, end, args.weeks))
    elif args.format == "json":
        print(json.dumps({**summary, "days": {d.isoformat(): n for d, n in sorted(counts.items())}},
                         indent=1))
    else:
        print(render_text(counts, end, args.weeks, STYLES[args.style]))
        print(f"\n{summary['commits']} commit(s) on {summary['active_days']} day(s), "
              f"{summary['from']} to {summary['to']}")
        if busiest:
            print(f"Busiest day: {busiest[0]} ({busiest[1]}); busiest weekday: "
                  f"{summary['busiest_weekday']}")
            print(f"Longest streak: {longest} day(s); current streak: {current} day(s)")
        print(f"Less {glyph_key(STYLES[args.style])} More")
    return 0


def glyph_key(glyphs):
    return "".join(f"[{g}]" for g in glyphs)


if __name__ == "__main__":
    sys.exit(main())
