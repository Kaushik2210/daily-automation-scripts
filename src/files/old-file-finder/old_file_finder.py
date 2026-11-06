"""Find files that have not been modified for a number of days."""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

DAY = 86400


def find_old_files(root, days, now=None):
    """Return (mtime, path) tuples for files older than `days`, oldest first."""
    cutoff = (time.time() if now is None else now) - days * DAY
    found = []
    for path in Path(root).rglob("*"):
        if path.is_file() and not path.is_symlink():
            mtime = path.stat().st_mtime
            if mtime < cutoff:
                found.append((mtime, path))
    return sorted(found)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find files not modified in N days.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--days", type=int, default=365, help="age threshold (default: 365)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    found = find_old_files(args.folder, args.days)
    for mtime, path in found:
        stamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        print(f"{stamp}  {path}")
    print(f"{len(found)} file(s) older than {args.days} days.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
