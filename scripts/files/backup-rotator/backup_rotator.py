"""Keep the newest N backups in a folder and prune the rest. Dry run by default."""
import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

STAMP = re.compile(r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})(?:[-_T ]?(\d{2})[-_:]?(\d{2})[-_:]?(\d{2}))?")


def human_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def entry_time(path):
    """The time a backup was made: read from its name (20261101-090000), else its modified time."""
    match = STAMP.search(path.name)
    if match:
        parts = [int(g) if g else 0 for g in match.groups()]
        try:
            return datetime(*parts), "name"
        except ValueError:
            pass
    return datetime.fromtimestamp(path.lstat().st_mtime), "file date"


def size_of(path):
    if path.is_symlink() or path.is_file():
        return path.lstat().st_size
    return sum(f.lstat().st_size for f in path.rglob("*") if f.is_file() and not f.is_symlink())


def choose(entries, keep, keep_monthly=0):
    """entries: [(time, path)]. Return (kept, doomed), each newest first, with reasons for kept."""
    ordered = sorted(entries, key=lambda e: (e[0], e[1].name), reverse=True)
    reasons = {ordered[i][1]: f"newest {keep}" for i in range(min(keep, len(ordered)))}
    if keep_monthly:
        months = []
        for when, path in ordered:
            month = (when.year, when.month)
            if month not in months and len(months) < keep_monthly:
                months.append(month)
                reasons.setdefault(path, f"latest of {when:%Y-%m}")
    kept = [(t, p, reasons[p]) for t, p in ordered if p in reasons]
    doomed = [(t, p) for t, p in ordered if p not in reasons]
    return kept, doomed


def remove(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Keep the newest N backups, prune the rest.")
    parser.add_argument("folder", type=Path, help="the folder that holds the backups")
    parser.add_argument("--pattern", required=True,
                        help="which entries are backups, e.g. 'project-*' or '*.zip'")
    parser.add_argument("--keep", type=int, required=True, help="how many of the newest to keep")
    parser.add_argument("--keep-monthly", type=int, default=0, metavar="M",
                        help="also keep the latest backup of each of the last M months")
    parser.add_argument("--apply", action="store_true", help="actually delete the old backups")
    args = parser.parse_args(argv)
    if args.keep < 1:
        parser.error("--keep must be at least 1, so the newest backup is never removed")
    if args.keep_monthly < 0:
        parser.error("--keep-monthly can't be negative")
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    if os.sep in args.pattern or "/" in args.pattern:
        parser.error("--pattern matches names inside the folder, so it can't contain slashes")

    matches = sorted(args.folder.glob(args.pattern))
    entries = [(entry_time(p)[0], p) for p in matches]
    if not entries:
        print(f"Nothing in {args.folder} matches '{args.pattern}'.")
        return 1
    kept, doomed = choose(entries, args.keep, args.keep_monthly)
    print(f"{len(entries)} backup(s) match '{args.pattern}': keeping {len(kept)}, "
          f"removing {len(doomed)}.")
    for when, path, why in kept:
        print(f"  keep    {path.name}  ({when:%Y-%m-%d %H:%M}, {why})")
    freed = 0
    for when, path in doomed:
        freed += size_of(path)
        print(f"  remove  {path.name}  ({when:%Y-%m-%d %H:%M})")
    if not doomed:
        print("Nothing to prune.")
        return 0
    if not args.apply:
        print(f"\nDry run - nothing deleted. --apply would free {human_size(freed)}.")
        return 0
    failed = 0
    for _, path in doomed:
        try:
            remove(path)
        except OSError as err:
            failed += 1
            print(f"could not remove {path.name}: {err}")
    print(f"\nRemoved {len(doomed) - failed} backup(s), freed up to {human_size(freed)}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
