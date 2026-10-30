"""List the files in a folder sorted by size, largest first."""
import argparse
import sys
from pathlib import Path


def human_size(num):
    size = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def list_sizes(folder, recursive=False):
    """Return (size, path) tuples sorted largest first."""
    pattern = "**/*" if recursive else "*"
    entries = []
    for path in Path(folder).glob(pattern):
        if path.is_file():
            entries.append((path.stat().st_size, path))
    return sorted(entries, key=lambda item: (-item[0], str(item[1])))


def main(argv=None):
    parser = argparse.ArgumentParser(description="List files sorted by size.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path("."))
    parser.add_argument("-r", "--recursive", action="store_true", help="include subfolders")
    parser.add_argument("-n", "--top", type=int, default=20, help="how many files to show")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    entries = list_sizes(args.folder, args.recursive)
    for size, path in entries[: args.top]:
        print(f"{human_size(size):>10}  {path.relative_to(args.folder)}")
    total = sum(size for size, _ in entries)
    print(f"{len(entries)} file(s), {human_size(total)} in total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
