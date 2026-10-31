"""Report total, used and free space for drives or folders."""
import argparse
import os
import shutil
import string
import sys
from pathlib import Path


def human_size(num):
    size = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def default_roots():
    """Drive letters on Windows, otherwise the root and home folders."""
    if os.name == "nt":
        return [Path(f"{letter}:/") for letter in string.ascii_uppercase
                if Path(f"{letter}:/").exists()]
    return [Path("/"), Path.home()]


def usage_for(path):
    """Return (total, used, free) in bytes for the disk holding `path`."""
    return tuple(shutil.disk_usage(path))


def bar(percent, width=20):
    filled = round(width * percent / 100)
    return "#" * filled + "-" * (width - filled)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report disk usage.")
    parser.add_argument("paths", nargs="*", type=Path, help="drives or folders (default: auto)")
    parser.add_argument("--warn", type=float, default=90, help="flag disks fuller than this %%")
    args = parser.parse_args(argv)

    full = False
    print(f"{'path':<14}{'total':>10}{'used':>10}{'free':>10}  usage")
    for path in args.paths or default_roots():
        try:
            total, used, free = usage_for(path)
        except OSError as err:
            print(f"{str(path):<14}  unavailable: {err}")
            continue
        percent = used / total * 100 if total else 0
        flag = "  <-- almost full" if percent >= args.warn else ""
        full = full or bool(flag)
        print(f"{str(path):<14}{human_size(total):>10}{human_size(used):>10}"
              f"{human_size(free):>10}  [{bar(percent)}] {percent:.0f}%{flag}")
    return 1 if full else 0


if __name__ == "__main__":
    sys.exit(main())
