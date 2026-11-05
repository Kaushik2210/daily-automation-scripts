"""Build a daily standup (yesterday / today / blockers) from your git commits."""
import argparse
import re
import subprocess  # web-ok: git only runs when no --log file is given
import sys
from datetime import date, timedelta
from pathlib import Path

US = "\x1f"
LOG_FORMAT = "@@%H%x1f%an%x1f%ae%x1f%ad%x1f%s"
TYPES = "feat|fix|docs|chore|refactor|test|style|perf|build|ci"
PREFIX = re.compile(rf"^(?:{TYPES})(?:\([^)]*\))?!?:\s*")


def parse_log(text):
    """Parse `git log --pretty=format:'@@%H%x1f%an%x1f%ae%x1f%ad%x1f%s' --date=short`."""
    commits = []
    for line in text.splitlines():
        if line.startswith("@@"):
            sha, name, email, day, subject = (line[2:].split(US) + [""] * 5)[:5]
            commits.append({"sha": sha, "name": name, "email": email, "date": day,
                            "subject": subject})
    return commits


def run_git(repo, *args):
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              encoding="utf-8", check=True)
    except (OSError, subprocess.CalledProcessError) as err:
        raise SystemExit(f"Couldn't run git in {repo}: {err}") from err
    return proc.stdout


def previous_workday(today):
    """Yesterday, or Friday when today is Monday (or the weekend)."""
    back = {0: 3, 6: 2}.get(today.weekday(), 1)
    return today - timedelta(days=back)


def friendly(subject):
    """'feat(ui): add dark mode' -> 'Add dark mode'."""
    text = PREFIX.sub("", subject).strip().rstrip(".")
    return text[:1].upper() + text[1:] if text else subject


def build_standup(commits, today, author="", raw=False):
    mine = [c for c in commits if author.lower() in f"{c['name']} {c['email']}".lower()]
    before = previous_workday(today)
    show = (lambda s: s) if raw else friendly

    def bullets(day):
        found = [c for c in mine if c["date"] == day.isoformat()]
        return [f"- {show(c['subject'])} ({c['sha'][:7]})" for c in found] or ["- (no commits)"]

    who = f" ({author})" if author else ""
    return "\n".join([
        f"Standup for {today:%a %Y-%m-%d}{who}", "",
        f"Yesterday ({before:%a %Y-%m-%d}):", *bullets(before), "",
        "Today so far:", *bullets(today), "",
        "Blockers:", "- None",
    ])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a daily standup from git commits.")
    parser.add_argument("--repo", type=Path, default=Path("."), help="git repository (default: .)")
    parser.add_argument("--log", type=Path, help="read a saved git log file instead of running git")
    parser.add_argument("--author", default="", help="only commits whose author name/email match")
    parser.add_argument("--today", help="treat this date as today, YYYY-MM-DD")
    parser.add_argument("--raw", action="store_true", help="keep the original commit subjects")
    args = parser.parse_args(argv)
    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
    except ValueError:
        parser.error("--today must look like 2026-01-13")

    if args.log:
        text = args.log.read_text(encoding="utf-8")
    else:
        since = (previous_workday(today) - timedelta(days=1)).isoformat()
        text = run_git(args.repo, "log", "--date=short", f"--since={since}",
                       f"--pretty=format:{LOG_FORMAT}")
    print(build_standup(parse_log(text), today, args.author, args.raw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
