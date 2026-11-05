"""Build a changelog section from conventional commits (feat, fix, docs ...)."""
import argparse
import re
import subprocess  # web-ok: git only runs when no --log file is given
import sys
from datetime import date
from pathlib import Path

US = "\x1f"
LOG_FORMAT = "@@%H%x1f%an%x1f%ae%x1f%ad%x1f%s"
SECTIONS = [("feat", "Features"), ("fix", "Bug fixes"), ("perf", "Performance"),
            ("refactor", "Refactoring"), ("docs", "Documentation"), ("build", "Build"),
            ("ci", "CI"), ("test", "Tests"), ("chore", "Chores"), ("style", "Style"),
            ("revert", "Reverts")]
SUBJECT = re.compile(r"^(\w+)(?:\(([^)]*)\))?(!)?:\s*(.+)$")


def parse_log(text):
    commits = []
    for line in text.splitlines():
        if line.startswith("@@"):
            sha, _name, _email, day, subject = (line[2:].split(US) + [""] * 5)[:5]
            commits.append({"sha": sha[:7], "date": day, "subject": subject})
    return commits


def run_git(repo, *args):
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              encoding="utf-8", check=True)
    except (OSError, subprocess.CalledProcessError) as err:
        raise SystemExit(f"Couldn't run git in {repo}: {err}") from err
    return proc.stdout


def since_args(since):
    """git arguments for --since: a date becomes --since=DATE, anything else is a tag or ref."""
    if not since:
        return []
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
        return [f"--since={since}"]
    return [f"{since}..HEAD"]


def group_commits(commits):
    """Return (breaking, {type: [entries]}, ignored_count) from conventional commit subjects."""
    groups, breaking, ignored = {}, [], 0
    known = dict(SECTIONS)
    for c in commits:
        match = SUBJECT.match(c["subject"])
        if not match or match.group(1).lower() not in known:
            ignored += 1
            continue
        kind, scope, bang, text = match.group(1).lower(), *match.group(2, 3, 4)
        entry = (f"**{scope}:** " if scope else "") + text.rstrip(".") + f" ({c['sha']})"
        groups.setdefault(kind, []).append(entry)
        if bang:
            breaking.append(entry)
    return breaking, groups, ignored


def render(commits, version, day):
    breaking, groups, ignored = group_commits(commits)
    lines = [f"## [{version}] - {day}", ""]
    if breaking:
        lines += ["### BREAKING CHANGES", "", *[f"- {e}" for e in breaking], ""]
    for kind, title in SECTIONS:
        if kind in groups:
            lines += [f"### {title}", "", *[f"- {e}" for e in groups[kind]], ""]
    if ignored:
        lines.append(f"_{ignored} commit(s) without a conventional prefix were left out._")
        lines.append("")
    return "\n".join(lines)


def add_to_file(existing, section):
    """Put the new section under the '# Changelog' title, above older entries."""
    if not existing.strip():
        return f"# Changelog\n\n{section}"
    head, sep, rest = existing.partition("\n## ")
    if not sep:
        return f"{existing.rstrip()}\n\n{section}"
    return f"{head.rstrip()}\n\n{section}\n## {rest}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a changelog from commits.")
    parser.add_argument("--repo", type=Path, default=Path("."), help="git repository (default: .)")
    parser.add_argument("--log", type=Path, help="read a saved git log file instead of running git")
    parser.add_argument("--since", help="only commits after this date or tag (git mode)")
    parser.add_argument("--version", default="Unreleased", help="version heading (Unreleased)")
    parser.add_argument("--date", default="", help="date for the heading (default: today)")
    parser.add_argument("-o", "--output", type=Path, help="add the section to this CHANGELOG file")
    parser.add_argument("--apply", action="store_true",
                        help="really update --output (default only prints the section)")
    args = parser.parse_args(argv)
    if args.log and not args.log.is_file():
        parser.error(f"log file not found: {args.log}")

    if args.log:
        text = args.log.read_text(encoding="utf-8")
    else:
        text = run_git(args.repo, "log", "--date=short", f"--pretty=format:{LOG_FORMAT}",
                       *since_args(args.since))
    section = render(parse_log(text), args.version, args.date or date.today().isoformat())
    if args.output and args.apply:
        old = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        args.output.write_text(add_to_file(old, section), encoding="utf-8")
        print(f"Updated {args.output}.")
    else:
        print(section)
        if args.output:
            print(f"(preview only: use --apply to update {args.output})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
