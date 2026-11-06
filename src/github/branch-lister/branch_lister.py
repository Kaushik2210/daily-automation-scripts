"""List local git branches with how long ago each was last committed to."""
import argparse
import subprocess  # web-ok: git only runs when no --refs file is given
import sys
from datetime import date
from pathlib import Path

US = "\x1f"
REF_FORMAT = "%(refname:short)%1f%(committerdate:short)%1f%(authorname)%1f%(subject)"


def parse_refs(text):
    """Parse `git for-each-ref` output in the format shown in the README."""
    branches = []
    for line in text.splitlines():
        parts = (line.split(US) + [""] * 4)[:4]
        if parts[0].strip():
            branches.append({"name": parts[0], "date": parts[1], "author": parts[2],
                             "subject": parts[3]})
    return branches


def run_git(repo, *args):
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              encoding="utf-8", check=True)
    except (OSError, subprocess.CalledProcessError) as err:
        raise SystemExit(f"Couldn't run git in {repo}: {err}") from err
    return proc.stdout


def age_days(branch, today):
    return (today - date.fromisoformat(branch["date"])).days


def describe_age(days):
    if days < 1:
        return "today"
    if days < 14:
        return f"{days}d ago"
    if days < 90:
        return f"{days // 7}w ago"
    if days < 730:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def main(argv=None):
    parser = argparse.ArgumentParser(description="List branches by last activity.")
    parser.add_argument("--repo", type=Path, default=Path("."), help="git repository (default: .)")
    parser.add_argument("--refs", type=Path, help="read a saved for-each-ref file instead of git")
    parser.add_argument("--stale-days", type=int, default=90, help="mark branches older than this")
    parser.add_argument("--today", help="treat this date as today, YYYY-MM-DD (for testing)")
    args = parser.parse_args(argv)
    if args.refs and not args.refs.is_file():
        parser.error(f"refs file not found: {args.refs}")
    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
    except ValueError:
        parser.error("--today must look like 2026-01-13")

    if args.refs:
        text = args.refs.read_text(encoding="utf-8")
    else:
        text = run_git(args.repo, "for-each-ref", "--sort=-committerdate", f"--format={REF_FORMAT}",
                       "refs/heads")
    branches = sorted(parse_refs(text), key=lambda b: b["date"], reverse=True)
    if not branches:
        print("No branches found.")
        return 0
    width = max(len(b["name"]) for b in branches)
    stale = 0
    for b in branches:
        days = age_days(b, today)
        flag = "  STALE" if days > args.stale_days else ""
        stale += bool(flag)
        print(f"{b['name']:<{width}}  {b['date']}  {describe_age(days):>8}  "
              f"{b['author']:<14}{b['subject'][:40]}{flag}")
    print(f"{len(branches)} branch(es), {stale} older than {args.stale_days} days.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
