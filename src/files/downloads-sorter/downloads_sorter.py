"""Move files from a downloads folder into YYYY-MM folders by modified date."""
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


def month_folder(path):
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m")


def plan_moves(folder):
    """Return (source, destination) pairs for loose files in the folder."""
    folder = Path(folder)
    moves = []
    for path in sorted(folder.iterdir()):
        if path.is_file() and not path.name.startswith("."):
            moves.append((path, folder / month_folder(path) / path.name))
    return moves


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sort downloads into year-month folders.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path.home() / "Downloads",
                        help="folder to sort (default: ~/Downloads)")
    parser.add_argument("--apply", action="store_true",
                        help="really move files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    moved = 0
    for src, dst in plan_moves(args.folder):
        if dst.exists():
            print(f"skip {src.name}: already exists in {dst.parent.name}/")
            continue
        print(f"{src.name} -> {dst.parent.name}/")
        if args.apply:
            dst.parent.mkdir(exist_ok=True)
            shutil.move(str(src), str(dst))
        moved += 1
    verb = "Moved" if args.apply else "Would move"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {moved} file(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
