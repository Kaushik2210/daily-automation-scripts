"""Find the biggest files under a folder, with a size threshold and exclusions."""
import argparse
import heapq
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

UNITS = {"B": 1, "K": 1024, "KB": 1024, "M": 1024**2, "MB": 1024**2,
         "G": 1024**3, "GB": 1024**3, "T": 1024**4, "TB": 1024**4}


def parse_size(text):
    """Turn '500', '10KB' or '1.5 GB' into bytes."""
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([A-Za-z]*)\s*", text)
    unit = match.group(2).upper() or "B" if match else None
    if not match or unit not in UNITS:
        raise ValueError(f"not a size: {text!r}")
    return int(float(match.group(1)) * UNITS[unit])


def human_size(num):
    size = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def find_large(root, top=20, min_size=0, exclude=()):
    """Return the `top` largest (size, mtime, path) tuples, biggest first."""
    skip = set(exclude)
    heap = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            path = Path(current) / name
            try:
                info = path.stat()
            except OSError:
                continue
            if info.st_size >= min_size and not path.is_symlink():
                heapq.heappush(heap, (info.st_size, info.st_mtime, str(path)))
                if len(heap) > top:
                    heapq.heappop(heap)
    return sorted(heap, reverse=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find the biggest files under a folder.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path("."))
    parser.add_argument("-n", "--top", type=int, default=20, help="how many files to list")
    parser.add_argument("--min-size", default="0", help="ignore smaller files, e.g. 50MB")
    parser.add_argument("--exclude", action="append", default=[], metavar="NAME",
                        help="folder name to skip (repeatable), e.g. node_modules")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    try:
        min_size = parse_size(args.min_size)
    except ValueError as err:
        parser.error(str(err))

    found = find_large(args.folder, args.top, min_size, args.exclude)
    for size, mtime, path in found:
        stamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        print(f"{human_size(size):>10}  {stamp}  {path}")
    total = sum(size for size, _, _ in found)
    print(f"{len(found)} file(s) listed, {human_size(total)} together "
          f"(scanned {time.strftime('%H:%M:%S')}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
