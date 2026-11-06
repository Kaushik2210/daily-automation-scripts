"""List TODO, FIXME and similar comments across a code base."""
import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path

DEFAULT_TAGS = ["TODO", "FIXME", "HACK", "XXX"]
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".idea"}
COMMENT_START = r"(?:#|//|/\*|<!--|--|;|\*)"
MAX_BYTES = 1024 * 1024


def make_pattern(tags):
    names = "|".join(re.escape(t) for t in tags)
    return re.compile(rf"{COMMENT_START}\s*({names})\b(?:\(([^)]*)\))?[:\s-]*(.*)", re.IGNORECASE)


def scan_text(text, pattern):
    """Return [(line_number, TAG, owner, message)] for each tagged comment."""
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        match = pattern.search(line)
        if match:
            message = match.group(3).replace("*/", "").replace("-->", "").strip()
            found.append((number, match.group(1).upper(), match.group(2) or "", message))
    return found


def scan_folder(root, tags):
    pattern = make_pattern(tags)
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            path = Path(current) / name
            try:
                if path.stat().st_size > MAX_BYTES:
                    continue
                text = path.read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for number, tag, owner, message in scan_text(text, pattern):
                yield path, number, tag, owner, message


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find TODO and FIXME comments.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--tags", nargs="+", default=DEFAULT_TAGS, help="tags to look for")
    parser.add_argument("--owner", default="", help="only comments like TODO(owner)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    counts, total = Counter(), 0
    for path, number, tag, owner, message in scan_folder(args.folder, args.tags):
        if args.owner and args.owner.lower() != owner.lower():
            continue
        who = f" ({owner})" if owner else ""
        print(f"{path.relative_to(args.folder).as_posix()}:{number}  {tag}{who}  {message}")
        counts[tag] += 1
        total += 1
    summary = ", ".join(f"{n} {tag}" for tag, n in counts.most_common())
    print(f"{total} comment(s) found" + (f": {summary}." if summary else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
