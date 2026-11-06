"""Record a folder's size over time in a CSV and show how it has changed."""
import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

HEADER = ["timestamp", "folder", "bytes", "files"]


def folder_stats(root):
    """Return (total_bytes, file_count) for everything under `root`."""
    total = count = 0
    for current, _dirs, files in os.walk(root):
        for name in files:
            path = Path(current) / name
            try:
                if not path.is_symlink():
                    total += path.stat().st_size
                    count += 1
            except OSError:
                continue
    return total, count


def human_size(num):
    size = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def record(log, folder, now=None):
    """Append the folder's current size to the CSV log and return the new row."""
    total, count = folder_stats(folder)
    row = [(now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"), str(folder), total, count]
    is_new = not log.exists() or log.stat().st_size == 0
    with log.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if is_new:
            writer.writerow(HEADER)
        writer.writerow(row)
    return row


def read_history(log, folder=None):
    with log.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [r for r in rows if folder is None or r["folder"] == str(folder)]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Track a folder's size over time.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--log", type=Path, default=Path("folder_sizes.csv"),
                        help="CSV file to append to (default: folder_sizes.csv)")
    parser.add_argument("--show", action="store_true",
                        help="show the history instead of recording a new entry")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    if not args.show:
        row = record(args.log, args.folder)
        print(f"Recorded {human_size(row[2])} in {row[3]} file(s) at {row[0]}.")
    if args.log.exists():
        previous = None
        for entry in read_history(args.log, args.folder):
            size = int(entry["bytes"])
            change = "" if previous is None else f"  ({human_size(size - previous)} change)"
            files = f"{entry['files']:>6} files"
            print(f"{entry['timestamp']}  {human_size(size):>10}  {files}{change}")
            previous = size
    return 0


if __name__ == "__main__":
    sys.exit(main())
