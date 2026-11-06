"""Warn when free disk space drops below a size or a percentage."""
import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

UNITS = {"B": 1, "K": 1024, "KB": 1024, "M": 1024**2, "MB": 1024**2,
         "G": 1024**3, "GB": 1024**3, "T": 1024**4, "TB": 1024**4}


def parse_size(text):
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([A-Za-z]*)\s*", text)
    unit = (match.group(2).upper() or "B") if match else None
    if not match or unit not in UNITS:
        raise ValueError(f"not a size: {text!r}")
    return int(float(match.group(1)) * UNITS[unit])


def check_space(path, min_free_bytes=0, min_free_percent=0):
    """Return (is_low, free_bytes, free_percent) for the disk holding `path`."""
    total, _used, free = shutil.disk_usage(path)
    percent = free / total * 100 if total else 0
    low = free < min_free_bytes or percent < min_free_percent
    return low, free, percent


def gb(num):
    return f"{num / 1024**3:.1f} GB"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Alert when free disk space is low.")
    parser.add_argument("paths", nargs="*", type=Path, default=[Path(".")],
                        help="folders or drives to check (default: current folder)")
    parser.add_argument("--min-free", default="10GB", help="alert below this much free space")
    parser.add_argument("--min-percent", type=float, default=0, help="alert below this %% free")
    parser.add_argument("--log", type=Path, help="append each result to this file")
    args = parser.parse_args(argv)
    try:
        min_free = parse_size(args.min_free)
    except ValueError as err:
        parser.error(str(err))

    any_low = False
    for path in args.paths:
        try:
            low, free, percent = check_space(path, min_free, args.min_percent)
        except OSError as err:
            print(f"ERROR {path}: {err}")
            any_low = True
            continue
        any_low = any_low or low
        line = f"{'LOW' if low else 'OK '}  {path}  {gb(free)} free ({percent:.0f}%)"
        print(line)
        if args.log:
            with args.log.open("a", encoding="utf-8") as handle:
                handle.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {line}\n")
    return 1 if any_low else 0


if __name__ == "__main__":
    sys.exit(main())
