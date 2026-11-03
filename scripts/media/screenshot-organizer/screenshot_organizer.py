"""File screenshots into year/month folders, using the date in the file name when there is one."""
import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
DEFAULT_PATTERN = r"screen ?shot|screenshot|snip|capture"
DATE_RE = re.compile(r"(20\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])")


def is_screenshot(path, pattern=DEFAULT_PATTERN):
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        return False
    return bool(re.search(pattern, path.stem, re.IGNORECASE))


def shot_date(path):
    """Date from the file name (2026-03-01, 20260301, 2026_03_01) or the modified time."""
    match = DATE_RE.search(path.stem)
    if match:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return datetime.fromtimestamp(path.stat().st_mtime)


def plan_moves(folder, pattern=DEFAULT_PATTERN, layout="year-month"):
    """Return (source, destination) pairs for screenshots directly inside `folder`."""
    folder = Path(folder)
    moves = []
    for path in sorted(folder.iterdir()):
        if path.is_file() and is_screenshot(path, pattern):
            day = shot_date(path)
            parts = (f"{day:%Y}", f"{day:%Y-%m}") if layout == "year-month" else (f"{day:%Y-%m}",)
            moves.append((path, folder.joinpath(*parts) / path.name))
    return moves


def main(argv=None):
    parser = argparse.ArgumentParser(description="Organize screenshots into dated folders.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--pattern", default=DEFAULT_PATTERN,
                        help="regex for file names that count as screenshots")
    parser.add_argument("--layout", choices=["year-month", "month"], default="year-month",
                        help="folders like 2026/2026-03 or just 2026-03")
    parser.add_argument("--apply", action="store_true",
                        help="really move the files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    try:
        re.compile(args.pattern)
    except re.error as err:
        parser.error(f"bad pattern: {err}")

    moved = 0
    for src, dst in plan_moves(args.folder, args.pattern, args.layout):
        if dst.exists():
            print(f"skip {src.name}: already in {dst.parent.relative_to(args.folder)}")
            continue
        print(f"{src.name} -> {dst.parent.relative_to(args.folder).as_posix()}/")
        if args.apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        moved += 1
    verb = "Moved" if args.apply else "Would move"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {moved} screenshot(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
