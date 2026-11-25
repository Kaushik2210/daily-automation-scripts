"""Scan a repository's git history for secrets, including ones that were deleted afterwards."""
import argparse
import json
import re
import subprocess  # web-ok: git only runs without --from-file; saved patches work anywhere
import sys
from pathlib import Path

PATTERNS = {
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "Stripe live key": re.compile(r"\b[rs]k_live_[0-9A-Za-z]{20,}\b"),
    "Private key block": re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    "Hard-coded credential": re.compile(
        r"""(?i)(?:api[_-]?key|secret|token|passwd|password)\w*['"]?\s*[:=]\s*['"]([^'"\s]{8,})['"]"""),
}
PLACEHOLDERS = ("example", "your_", "your-", "changeme", "xxxx", "placeholder", "<", "${", "dummy")


def mask(text):
    """Show only the first and last 3 characters, never the whole secret."""
    return text if len(text) <= 8 else f"{text[:3]}{'*' * min(len(text) - 6, 10)}{text[-3:]}"


def find_secrets(line, include_placeholders=False):
    """[(kind, raw value)] found on one line."""
    found = []
    for kind, pattern in PATTERNS.items():
        match = pattern.search(line)
        if not match:
            continue
        raw = match.group(1) if match.groups() else match.group(0)
        if not include_placeholders and any(p in raw.lower() for p in PLACEHOLDERS):
            continue
        found.append((kind, raw))
    return found


def scan_patch(text, include_placeholders=False):
    """Walk `git log -p` output and return findings with whether each was later removed."""
    commit = {"sha": "", "author": "", "date": ""}
    path, in_hunk, findings, removed = "", False, [], {}
    for line in text.splitlines():
        if line.startswith("commit "):  # diff content always starts with +, - or a space
            commit = {"sha": line.split()[1], "author": "", "date": ""}
            in_hunk = False
        elif line.startswith("diff --git"):
            in_hunk = False
        elif line.startswith("@@"):
            in_hunk = True
        elif not in_hunk:
            if line.startswith("Author:"):
                commit["author"] = line[7:].strip()
            elif line.startswith("Date:"):
                commit["date"] = line[5:].strip()
            elif line.startswith("+++ b/"):
                path = line[6:]
            elif line.startswith("--- a/"):
                path = line[6:]  # replaced by +++ b/ unless the file was deleted
        elif line.startswith("+"):
            for kind, raw in find_secrets(line[1:], include_placeholders):
                findings.append({"kind": kind, "path": path, "commit": commit["sha"],
                                 "author": commit["author"], "date": commit["date"],
                                 "masked": mask(raw), "removed_in": None, "_raw": raw})
        elif line.startswith("-"):
            for _, raw in find_secrets(line[1:], include_placeholders):
                removed.setdefault((path, raw), commit["sha"])
    for item in findings:
        gone = removed.get((item["path"], item["_raw"]))
        if gone and gone != item["commit"]:
            item["removed_in"] = gone
        del item["_raw"]
    return findings


def git_patch(repo, since, max_count):
    command = ["git", "-C", str(repo), "log", "-p", "--all", "-U0", "--no-color", "--no-ext-diff"]
    if since:
        command.append(f"--since={since}")
    if max_count:
        command.append(f"--max-count={max_count}")
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=900, check=False)
    if result.returncode:
        raise OSError((result.stderr.strip().splitlines() or ["git log failed"])[-1])
    return result.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find secrets anywhere in git history.")
    parser.add_argument("--repo", type=Path, default=Path("."), help="the repository (.)")
    parser.add_argument("--from-file", type=Path, dest="source",
                        help="a saved `git log -p` output instead of running git")
    parser.add_argument("--since", help="only commits after this, e.g. '6 months ago'")
    parser.add_argument("--max-count", type=int, default=0, help="only the newest N commits")
    parser.add_argument("--include-placeholders", action="store_true",
                        help="also report values that look like examples or placeholders")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--exit-zero", action="store_true", help="exit 0 even when secrets exist")
    args = parser.parse_args(argv)
    try:
        text = (args.source.read_text(encoding="utf-8", errors="replace") if args.source
                else git_patch(args.repo, args.since, args.max_count))
    except (OSError, subprocess.SubprocessError) as err:
        print(f"Can't read the history: {err}", file=sys.stderr)
        return 1
    findings = scan_patch(text, args.include_placeholders)

    if args.format == "json":
        print(json.dumps({"count": len(findings), "findings": findings}, indent=1))
    elif not findings:
        print("No secrets found in the history.")
    else:
        print(f"{len(findings)} possible secret(s) in the history:\n")
        for item in findings:
            state = (f"removed in {item['removed_in'][:8]}, still in history"
                     if item["removed_in"] else "still present in a later version")
            print(f"  {item['kind']}: {item['masked']}")
            print(f"    {item['path']}  commit {item['commit'][:8]} by {item['author']}")
            print(f"    {item['date']}  ({state})")
        print("\nA secret that was ever committed must be treated as leaked: rotate it first, "
              "then clean the history if you need to.")
    return 0 if args.exit_zero or not findings else 1


if __name__ == "__main__":
    sys.exit(main())
