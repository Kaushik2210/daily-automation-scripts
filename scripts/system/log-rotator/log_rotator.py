"""Rotate and compress big log files, keeping a few old copies. Dry run by default."""
import argparse
import gzip
import os
import re
import sys
from pathlib import Path

UNITS = {"": 1, "B": 1, "K": 1024, "KB": 1024, "M": 1024 ** 2, "MB": 1024 ** 2,
         "G": 1024 ** 3, "GB": 1024 ** 3}


def parse_size(text):
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([A-Za-z]*)\s*", text)
    if not match or match.group(2).upper() not in UNITS:
        raise argparse.ArgumentTypeError("size must look like 500KB, 10MB or 2G")
    size = int(float(match.group(1)) * UNITS[match.group(2).upper()])
    if size < 1:
        raise argparse.ArgumentTypeError("size must be at least 1 byte")
    return size


def human_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def archive_name(log, number):
    return log.with_name(f"{log.name}.{number}.gz")


def find_logs(paths, pattern):
    found = []
    for path in paths:
        if path.is_dir():
            found += sorted(p for p in path.glob(pattern) if p.is_file() and not p.is_symlink())
        elif path.is_file():
            found.append(path)
    return found


def plan_rotation(log, keep):
    """Return the renames and deletions needed to make room for a new .1.gz archive."""
    steps = []
    existing = sorted(int(m.group(1)) for p in log.parent.glob(log.name + ".*.gz")
                      if (m := re.fullmatch(re.escape(log.name) + r"\.(\d+)\.gz", p.name)))
    for number in reversed(existing):
        if number + 1 > keep:
            steps.append(("delete", archive_name(log, number), None))
        else:
            steps.append(("rename", archive_name(log, number), archive_name(log, number + 1)))
    return steps


def rotate(log, keep, rename_log):
    """Compress the log into name.1.gz after shifting the older archives up by one."""
    for action, source, target in plan_rotation(log, keep):
        if action == "delete":
            source.unlink()
        else:
            os.replace(source, target)
    temp = log.with_name(log.name + ".new.gz")
    snapshot = log.stat().st_size  # archive exactly this many bytes, even if the log keeps growing
    try:
        with log.open("rb") as raw, gzip.open(temp, "wb") as packed:
            remaining = snapshot
            while remaining:
                chunk = raw.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                packed.write(chunk)
                remaining -= len(chunk)
        with gzip.open(temp, "rb") as check:  # make sure the archive reads back completely
            stored = sum(len(c) for c in iter(lambda: check.read(1024 * 1024), b""))
        if stored != snapshot:
            raise OSError("the compressed copy doesn't match the log; nothing was changed")
        if rename_log and log.stat().st_size != snapshot:
            raise OSError("the log grew while it was being copied; run again to rotate it")
        os.replace(temp, archive_name(log, 1))
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    if rename_log:
        log.unlink()
    else:
        with log.open("r+b") as handle:  # copytruncate: the program keeps its open file handle
            handle.seek(snapshot)
            tail = handle.read()  # anything written after the snapshot stays in the log
            handle.seek(0)
            handle.truncate(0)
            handle.write(tail)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rotate and compress big log files.")
    parser.add_argument("paths", nargs="+", type=Path, help="log files, or folders of logs")
    parser.add_argument("--max-size", type=parse_size, required=True,
                        help="rotate files at least this big, e.g. 10MB")
    parser.add_argument("--keep", type=int, default=5, help="compressed archives to keep (5)")
    parser.add_argument("--pattern", default="*.log", help="which files in a folder (*.log)")
    parser.add_argument("--rename", action="store_true",
                        help="remove the log after archiving it instead of emptying it in place")
    parser.add_argument("--apply", action="store_true", help="actually rotate the logs")
    args = parser.parse_args(argv)
    if args.keep < 1:
        parser.error("--keep must be at least 1")
    for path in args.paths:
        if not path.exists():
            parser.error(f"not found: {path}")

    logs = find_logs(args.paths, args.pattern)
    big = [log for log in logs if log.stat().st_size >= args.max_size]
    print(f"{len(logs)} log file(s), {len(big)} at least {human_size(args.max_size)}.")
    for log in logs:
        size = log.stat().st_size
        if log not in big:
            print(f"  skip    {log.name}  ({human_size(size)})")
            continue
        mode = "removed" if args.rename else "emptied in place"
        print(f"  rotate  {log.name}  ({human_size(size)}) -> {archive_name(log, 1).name}, "
              f"original {mode}")
        for action, source, target in plan_rotation(log, args.keep):
            print(f"            {'delete' if action == 'delete' else 'rename'} {source.name}"
                  + (f" -> {target.name}" if target else " (older than --keep)"))
    if not args.apply:
        print("\nDry run - nothing changed. Add --apply to rotate." if big else
              "\nNothing needs rotating.")
        return 0
    failed = 0
    for log in big:
        try:
            rotate(log, args.keep, args.rename)
        except OSError as err:
            failed += 1
            print(f"could not rotate {log.name}: {err}")
    print(f"\nRotated {len(big) - failed} file(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
