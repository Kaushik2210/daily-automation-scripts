"""Sort the files in a folder into subfolders based on their extension."""
import argparse
import shutil
import sys
from pathlib import Path

CATEGORIES = {
    "images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".heic"},
    "documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".odt", ".rtf", ".ppt", ".pptx"},
    "spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
    "audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
    "video": {".mp4", ".mkv", ".mov", ".avi", ".webm"},
    "archives": {".zip", ".tar", ".gz", ".7z", ".rar", ".bz2"},
    "code": {".py", ".js", ".ts", ".html", ".css", ".json", ".java", ".c", ".cpp", ".sh"},
}


def folder_for(path, by_extension=False):
    ext = path.suffix.lower()
    if by_extension:
        return ext.lstrip(".") or "no_extension"
    for name, extensions in CATEGORIES.items():
        if ext in extensions:
            return name
    return "other"


def plan_moves(folder, by_extension=False):
    moves = []
    for path in sorted(Path(folder).iterdir()):
        if path.is_file() and not path.name.startswith("."):
            moves.append((path, path.parent / folder_for(path, by_extension) / path.name))
    return moves


def main(argv=None):
    parser = argparse.ArgumentParser(description="Organize a folder by file type.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--by-extension", action="store_true",
                        help="one folder per extension instead of broad categories")
    parser.add_argument("--apply", action="store_true",
                        help="really move files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    moved = 0
    for src, dst in plan_moves(args.folder, args.by_extension):
        if dst.exists():
            print(f"skip {src.name}: {dst.parent.name}/{dst.name} already exists")
            continue
        print(f"{src.name} -> {dst.parent.name}/")
        if args.apply:
            dst.parent.mkdir(exist_ok=True)
            shutil.move(str(src), str(dst))
        moved += 1
    verb = "Moved" if args.apply else "Would move"
    print(f"{verb} {moved} file(s)." + ("" if args.apply else " Use --apply to do it."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
