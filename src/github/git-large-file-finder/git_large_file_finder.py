"""Find the biggest files in a repository's whole git history, including ones deleted long ago."""
import argparse
import json
import re
import subprocess  # web-ok: git only runs without --from-file; saved listings work anywhere
import sys
from pathlib import Path

UNITS = {"": 1, "b": 1, "k": 1024, "m": 1024**2, "g": 1024**3}


def parse_size(text):
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kmgb]?)(?:i?b)?\s*", str(text).lower())
    if not match:
        raise ValueError(f"not a size: '{text}' (try 500k, 10M, 1G)")
    return int(float(match.group(1)) * UNITS[match.group(2)])


def human(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def parse_objects(text):
    """Lines of `type sha size path` (git cat-file --batch-check) -> [(sha, size, path)] blobs."""
    blobs = []
    for line in text.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) == 4 and parts[0] == "blob" and parts[2].isdigit():
            blobs.append((parts[1], int(parts[2]), parts[3]))
    return blobs


def summarise(blobs, head_paths=None):
    """Group blob versions by path: [{path, versions, largest, total, in_head}], biggest first.

    A blob that appears under several names is counted once, under the first name seen.
    """
    seen, paths = set(), {}
    for sha, size, path in blobs:
        if sha in seen:
            continue
        seen.add(sha)
        entry = paths.setdefault(path, {"path": path, "versions": 0, "largest": 0, "total": 0})
        entry["versions"] += 1
        entry["total"] += size
        entry["largest"] = max(entry["largest"], size)
    for entry in paths.values():
        entry["in_head"] = None if head_paths is None else entry["path"] in head_paths
    return sorted(paths.values(), key=lambda e: (-e["largest"], e["path"]))


def git(repo, *args, stdin=None):
    result = subprocess.run(["git", "-C", str(repo), *args], input=stdin, capture_output=True,
                            text=True, timeout=600, check=False)
    if result.returncode:
        raise OSError((result.stderr.strip().splitlines() or ["git failed"])[-1])
    return result.stdout


def read_repo(repo, ref):
    """Return (`type sha size path` lines, set of paths in the latest commit)."""
    listed = git(repo, "rev-list", "--objects", "--all" if ref == "all" else ref).splitlines()
    named = [line.split(" ", 1) for line in listed if " " in line]  # drops path-less commits
    shas = "".join(f"{sha}\n" for sha, _ in named)
    info = git(repo, "cat-file", "--batch-check=%(objecttype) %(objectname) %(objectsize)",
               stdin=shas).splitlines()
    lines = [f"{described} {path}" for described, (_, path) in zip(info, named, strict=True)]
    head = set(git(repo, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
    return "\n".join(lines), head


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find the largest files in git history.")
    parser.add_argument("--repo", type=Path, default=Path("."), help="the repository (.)")
    parser.add_argument("--from-file", type=Path, dest="source",
                        help="saved `type sha size path` lines instead of running git")
    parser.add_argument("--ref", default="all",
                        help="branch or tag to scan, or 'all' for every branch and tag (all)")
    parser.add_argument("--min-size", default="1M", help="ignore files smaller than this (1M)")
    parser.add_argument("--top", type=int, default=20, help="show this many files (20)")
    parser.add_argument("--only-removed", action="store_true",
                        help="only files that are no longer in the latest commit")
    parser.add_argument("--fail-over", help="exit 1 if a file in the latest commit is bigger")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    try:
        minimum = parse_size(args.min_size)
        limit = parse_size(args.fail_over) if args.fail_over else None
    except ValueError as err:
        parser.error(str(err))
    try:
        if args.source:
            text, head = args.source.read_text(encoding="utf-8"), None
        else:
            text, head = read_repo(args.repo, args.ref)
    except (OSError, subprocess.SubprocessError) as err:
        print(f"Can't read the history: {err}", file=sys.stderr)
        return 1

    entries = [e for e in summarise(parse_objects(text), head) if e["largest"] >= minimum]
    if args.only_removed:
        entries = [e for e in entries if e["in_head"] is False]
    too_big = [e for e in entries if limit and e["in_head"] and e["largest"] > limit]
    shown = entries[:args.top] if args.top else entries
    if args.format == "json":
        print(json.dumps({"files": shown, "count": len(entries)}, indent=1))
    elif not entries:
        print(f"Nothing at or above {human(minimum)}.")
    else:
        print(f"{len(entries)} file(s) at or above {human(minimum)}, biggest first:\n")
        for e in shown:
            notes = [{True: "in latest", False: "removed", None: ""}[e["in_head"]]]
            if e["versions"] > 1:
                notes.append(f"{e['versions']} versions")
            notes = ", ".join(n for n in notes if n)
            print(f"  {human(e['largest']):>9}  {e['path']}" + (f"  ({notes})" if notes else ""))
        gone = [e for e in shown if e["in_head"] is False]
        if gone:
            print(f"\n{len(gone)} are gone from the latest commit but still bloat the history. "
                  "To drop one for good (rewrites history, so coordinate first):")
            print(f"  git filter-repo --path {gone[0]['path']} --invert-paths")
    if too_big:
        print(f"\n{len(too_big)} file(s) in the latest commit exceed {human(limit)}.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
