"""Count files and total size per extension in a folder tree."""
import argparse
import sys
from collections import defaultdict
from pathlib import Path


def count_extensions(root):
    """Return {extension: [file_count, total_bytes]}; files without one use '(none)'."""
    stats = defaultdict(lambda: [0, 0])
    for path in Path(root).rglob("*"):
        if path.is_file() and not path.is_symlink():
            ext = path.suffix.lower() or "(none)"
            stats[ext][0] += 1
            stats[ext][1] += path.stat().st_size
    return dict(stats)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Count files per extension.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path("."))
    parser.add_argument("-n", "--top", type=int, default=0, help="show only the top N rows")
    parser.add_argument("--by-size", action="store_true", help="sort by total size, not count")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    stats = count_extensions(args.folder)
    key = 1 if args.by_size else 0
    rows = sorted(stats.items(), key=lambda item: (-item[1][key], item[0]))
    if args.top:
        rows = rows[: args.top]
    print(f"{'extension':<12}{'files':>8}{'bytes':>14}")
    for ext, (count, size) in rows:
        print(f"{ext:<12}{count:>8}{size:>14}")
    print(f"{sum(c for c, _ in stats.values())} file(s), {len(stats)} extension(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
