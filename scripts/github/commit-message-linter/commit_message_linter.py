"""Check commit messages against a format: conventional commits, length and tidiness."""
import argparse
import re
import subprocess  # web-ok: git only runs when no --log or --message is given
import sys
from pathlib import Path

US = "\x1f"
LOG_FORMAT = "@@%H%x1f%an%x1f%ae%x1f%ad%x1f%s"
TYPES = ["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore",
         "revert"]
CONVENTIONAL = re.compile(rf"^({'|'.join(TYPES)})(\([\w./-]+\))?(!)?: (\S.*)$")
VAGUE = {"wip", "fix", "fixes", "update", "updates", "changes", "stuff", "misc", "temp", "asdf"}


def lint_subject(subject, style="conventional", max_length=72):
    """Return a list of problems found in one commit subject line."""
    problems = []
    if len(subject) > max_length:
        problems.append(f"subject is {len(subject)} characters (limit {max_length})")
    if subject.rstrip().endswith("."):
        problems.append("subject ends with a period")
    if subject != subject.strip():
        problems.append("subject has leading or trailing spaces")
    if style == "conventional":
        match = CONVENTIONAL.match(subject)
        if not match:
            problems.append(f"not in the form 'type: description' (types: {', '.join(TYPES)})")
        elif match.group(4)[:1].isupper() and not match.group(4).split()[0].isupper():
            problems.append("description should start with a lowercase letter")
    if subject.strip().lower() in VAGUE:
        problems.append("subject is too vague to be useful")
    return problems


def parse_subjects(text):
    """Pull (sha, subject) pairs out of a saved git log."""
    found = []
    for line in text.splitlines():
        if line.startswith("@@"):
            parts = (line[2:].split(US) + [""] * 5)[:5]
            found.append((parts[0][:7], parts[4]))
    return found


def run_git(repo, *args):
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              encoding="utf-8", check=True)
    except (OSError, subprocess.CalledProcessError) as err:
        raise SystemExit(f"Couldn't run git in {repo}: {err}") from err
    return proc.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lint commit messages.")
    parser.add_argument("--message", help="check this one commit message")
    parser.add_argument("--log", type=Path, help="check a saved git log file")
    parser.add_argument("--repo", type=Path, default=Path("."), help="git repository (default: .)")
    parser.add_argument("-n", "--count", type=int, default=20, help="recent commits to check (20)")
    parser.add_argument("--style", choices=["conventional", "free"], default="conventional",
                        help="'free' only checks length and tidiness")
    parser.add_argument("--max-length", type=int, default=72, help="longest allowed subject (72)")
    args = parser.parse_args(argv)
    if args.log and not args.log.is_file():
        parser.error(f"log file not found: {args.log}")

    if args.message is not None:
        items = [("message", args.message.splitlines()[0] if args.message else "")]
    elif args.log:
        items = parse_subjects(args.log.read_text(encoding="utf-8"))
    else:
        text = run_git(args.repo, "log", f"-{args.count}", "--date=short",
                       f"--pretty=format:{LOG_FORMAT}")
        items = parse_subjects(text)
    bad = 0
    for sha, subject in items:
        problems = lint_subject(subject, args.style, args.max_length)
        if problems:
            bad += 1
            print(f"{sha}  {subject[:60]}{'...' if len(subject) > 60 else ''}")
            for problem in problems:
                print(f"        - {problem}")
    print(f"{len(items)} message(s) checked, {bad} with problems.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
