"""Work out the next semantic version from commit messages, and optionally create the git tag."""
import argparse
import re
import subprocess  # web-ok: git is only run without --log-file; saved commit lists work anywhere
import sys
from pathlib import Path

SEMVER = re.compile(r"^(?P<prefix>\D*)(\d+)\.(\d+)\.(\d+)(?P<rest>.*)$")
CONVENTIONAL = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\([^)]*\))?(?P<bang>!)?:\s*(?P<text>.+)$")
LEVEL = {"none": 0, "patch": 1, "minor": 2, "major": 3}


def classify(message):
    """Return (bump level, category) for one commit message."""
    subject = message.strip().splitlines()[0] if message.strip() else ""
    match = CONVENTIONAL.match(subject)
    breaking = bool(re.search(r"^BREAKING[ -]CHANGE:", message, re.MULTILINE))
    if match:
        kind = match.group("type").lower()
        if match.group("bang") or breaking:
            return "major", "breaking"
        if kind == "feat":
            return "minor", "feature"
        if kind in ("fix", "perf"):
            return "patch", "fix"
        return "none", "other"
    return ("major", "breaking") if breaking else ("none", "other")


def bump_version(current, level):
    match = SEMVER.match(current)
    if not match:
        raise ValueError(f"'{current}' is not a version like v1.2.3")
    major, minor, patch = int(match.group(2)), int(match.group(3)), int(match.group(4))
    if level == "major":
        major, minor, patch = major + 1, 0, 0
    elif level == "minor":
        minor, patch = minor + 1, 0
    elif level == "patch":
        patch += 1
    return f"{match.group('prefix')}{major}.{minor}.{patch}"


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                            timeout=60, check=False)
    if result.returncode:
        raise OSError((result.stderr.strip().splitlines() or ["git failed"])[-1])
    return result.stdout


def git_state(repo):
    """Return (latest tag or None, [commit messages since it])."""
    try:
        tag = git(repo, "describe", "--tags", "--abbrev=0", "--match", "[vV0-9]*").strip()
    except OSError:
        tag = None
    span = f"{tag}..HEAD" if tag else "HEAD"
    raw = git(repo, "log", span, "--format=%B%x1e")
    return tag, [m.strip() for m in raw.split("\x1e") if m.strip()]


def split_log(text):
    """Saved commits: one subject per line (a BREAKING CHANGE: line joins the previous one)."""
    messages = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith(("BREAKING CHANGE", "BREAKING-CHANGE")) and messages:
            messages[-1] += "\n\n" + line
        else:
            messages.append(line.strip())
    return messages


def main(argv=None):
    parser = argparse.ArgumentParser(description="Suggest the next version from commit messages.")
    parser.add_argument("--repo", type=Path, default=Path("."), help="git repository (.)")
    parser.add_argument("--log-file", type=Path,
                        help="saved commit subjects, one per line (instead of reading git)")
    parser.add_argument("--current", help="the current version, e.g. v1.4.2 (with --log-file)")
    parser.add_argument("--apply", action="store_true",
                        help="create the annotated git tag (never pushed)")
    args = parser.parse_args(argv)

    try:
        if args.log_file:
            if not args.current:
                parser.error("--log-file needs --current, e.g. --current v1.4.2")
            if args.apply:
                parser.error("--apply only works when reading a git repository")
            tag, messages = args.current, split_log(args.log_file.read_text(encoding="utf-8"))
        else:
            tag, messages = git_state(args.repo)
            tag = tag or "v0.0.0"
    except (OSError, subprocess.TimeoutExpired) as err:
        print(f"Can't read the history: {err}", file=sys.stderr)
        return 1
    if not messages:
        print(f"No new commits since {tag}; nothing to release.")
        return 0

    level, groups = "none", {"breaking": [], "feature": [], "fix": [], "other": []}
    for message in messages:
        kind, category = classify(message)
        groups[category].append(message.splitlines()[0])
        level = max(level, kind, key=LEVEL.get)
    try:
        new = bump_version(tag, level)
    except ValueError as err:
        print(err, file=sys.stderr)
        return 1
    print(f"Current version: {tag}   ({len(messages)} commit(s) since)")
    for title, key in (("Breaking changes", "breaking"), ("Features", "feature"),
                       ("Fixes", "fix"), ("Other (no release on their own)", "other")):
        if groups[key]:
            print(f"\n{title}:")
            print("\n".join(f"  - {line}" for line in groups[key]))
    if level == "none":
        print("\nOnly housekeeping commits: no new release is needed.")
        return 0
    print(f"\nNext version: {new}  ({level} bump)")
    if not args.apply:
        print("Dry run. Use --apply to create the tag in the repository.")
        return 0
    try:
        git(args.repo, "rev-parse", "--verify", f"refs/tags/{new}")
    except OSError:
        notes = "\n".join(f"- {line}" for key in ("breaking", "feature", "fix")
                          for line in groups[key])
        git(args.repo, "tag", "-a", new, "-m", f"Release {new}\n\n{notes}")
        print(f"Created tag {new}. Push it with: git push origin {new}")
        return 0
    print(f"The tag {new} already exists; nothing was changed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
