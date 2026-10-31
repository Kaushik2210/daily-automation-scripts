"""Remove old files from the temp folder (or any folder you name), dry run first."""
import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

DAY = 86400


def human_size(num):
    size = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def is_protected(path):
    """Never clean a drive root or the home folder itself."""
    path = path.resolve()
    return path == Path(path.anchor) or path == Path.home().resolve()


def old_files(root, days, now=None):
    """Return (path, size) for regular files not modified in `days` days."""
    cutoff = (time.time() if now is None else now) - days * DAY
    found = []
    for current, _dirs, files in os.walk(root):
        for name in files:
            path = Path(current) / name
            try:
                info = path.lstat()
            except OSError:
                continue
            if not path.is_symlink() and info.st_mtime < cutoff:
                found.append((path, info.st_size))
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description="Clear old files from temp folders.")
    parser.add_argument("folders", nargs="*", type=Path,
                        help="folders to clean (default: the system temp folder)")
    parser.add_argument("--days", type=int, default=7, help="only files older than this (7)")
    parser.add_argument("--apply", action="store_true",
                        help="really delete files (default is a dry run)")
    args = parser.parse_args(argv)

    deleted = freed = failed = 0
    for folder in args.folders or [Path(tempfile.gettempdir())]:
        if not folder.is_dir():
            print(f"skip {folder}: not a folder")
            continue
        if is_protected(folder):
            print(f"skip {folder}: refusing to clean a drive root or home folder")
            continue
        for path, size in old_files(folder, args.days):
            print(f"{human_size(size):>10}  {path}")
            if args.apply:
                try:
                    path.unlink()
                except OSError:
                    failed += 1
                    continue
            deleted += 1
            freed += size
    verb = "Deleted" if args.apply else "Would delete"
    hint = "" if args.apply else " Use --apply to do it."
    extra = f" {failed} file(s) were in use and skipped." if failed else ""
    print(f"{verb} {deleted} file(s), {human_size(freed)}.{extra}{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
