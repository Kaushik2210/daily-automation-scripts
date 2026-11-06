"""List and optionally remove empty directories, including nested empty ones."""
import argparse
import os
import sys
from pathlib import Path


def find_empty_dirs(root):
    """Return empty directories, deepest first. A folder holding only empty folders counts."""
    root = Path(root)
    empty = set()
    ordered = []
    for current, dirs, files in os.walk(root, topdown=False):
        path = Path(current)
        if path == root:
            continue
        if not files and all(path / d in empty for d in dirs):
            empty.add(path)
            ordered.append(path)
    return ordered


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find and remove empty folders.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--apply", action="store_true",
                        help="really remove folders (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    empty = find_empty_dirs(args.folder)
    for path in empty:
        print(path)
        if args.apply:
            path.rmdir()
    verb = "Removed" if args.apply else "Would remove"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {len(empty)} empty folder(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
