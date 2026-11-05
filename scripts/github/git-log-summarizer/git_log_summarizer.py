"""Summarize git history: commits per author, per week and per type of change."""
import argparse
import re
import subprocess  # web-ok: git only runs when no --log file is given
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

US = "\x1f"
LOG_FORMAT = "@@%H%x1f%an%x1f%ae%x1f%ad%x1f%s"
TYPE_RE = re.compile(r"^(\w+)(?:\([^)]*\))?!?:")


def parse_log(text):
    commits = []
    for line in text.splitlines():
        if line.startswith("@@"):
            sha, name, email, day, subject = (line[2:].split(US) + [""] * 5)[:5]
            commits.append({"sha": sha, "name": name, "date": day, "subject": subject})
    return commits


def run_git(repo, *args):
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              encoding="utf-8", check=True)
    except (OSError, subprocess.CalledProcessError) as err:
        raise SystemExit(f"Couldn't run git in {repo}: {err}") from err
    return proc.stdout


def week_label(day_text):
    year, week, _ = date.fromisoformat(day_text).isocalendar()
    return f"{year}-W{week:02d}"


def commit_type(subject):
    match = TYPE_RE.match(subject)
    return match.group(1).lower() if match else "other"


def summarize(commits):
    """Return dict with per-author, per-week (by author) and per-type counts."""
    by_author = Counter(c["name"] for c in commits)
    by_week = defaultdict(Counter)
    for c in commits:
        by_week[week_label(c["date"])][c["name"]] += 1
    by_type = Counter(commit_type(c["subject"]) for c in commits)
    return {"authors": by_author, "weeks": dict(sorted(by_week.items())), "types": by_type}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarize commits by author, week and type.")
    parser.add_argument("--repo", type=Path, default=Path("."), help="git repository (default: .)")
    parser.add_argument("--log", type=Path, help="read a saved git log file instead of running git")
    parser.add_argument("--since", help="only commits after this date, e.g. 2026-01-01 (git mode)")
    args = parser.parse_args(argv)

    if args.log:
        text = args.log.read_text(encoding="utf-8")
    else:
        extra = [f"--since={args.since}"] if args.since else []
        text = run_git(args.repo, "log", "--date=short", f"--pretty=format:{LOG_FORMAT}", *extra)
    commits = parse_log(text)
    if not commits:
        print("No commits found.")
        return 0
    summary = summarize(commits)
    authors = [name for name, _ in summary["authors"].most_common()]
    print(f"{len(commits)} commit(s) by {len(authors)} author(s)\n")
    print("By author")
    for name, count in summary["authors"].most_common():
        print(f"  {count:>4}  {name}")
    print("\nBy week" + " " * 7 + "  ".join(f"{a.split()[0][:8]:>8}" for a in authors) + "   total")
    for week, counts in summary["weeks"].items():
        cells = "  ".join(f"{counts.get(a, 0):>8}" for a in authors)
        print(f"  {week}  {cells}  {sum(counts.values()):>6}")
    print("\nBy type")
    for kind, count in summary["types"].most_common():
        print(f"  {count:>4}  {kind}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
