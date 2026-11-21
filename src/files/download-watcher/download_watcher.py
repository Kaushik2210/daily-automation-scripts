"""Sort files in your Downloads folder into subfolders (Images, Documents...) as they arrive."""
import argparse
import fnmatch
import shutil
import sys
import time
from pathlib import Path

CATEGORIES = {
    "Images": {"jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "heic", "tiff", "ico"},
    "Documents": {"pdf", "doc", "docx", "odt", "txt", "rtf", "md", "ppt", "pptx", "xls", "xlsx",
                  "epub"},
    "Data": {"csv", "json", "xml", "yaml", "yml", "sql", "db", "sqlite", "parquet"},
    "Archives": {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz"},
    "Audio": {"mp3", "wav", "flac", "aac", "ogg", "m4a", "opus"},
    "Video": {"mp4", "mkv", "mov", "avi", "webm", "wmv", "flv"},
    "Installers": {"exe", "msi", "dmg", "pkg", "deb", "rpm", "appimage", "apk"},
    "Code": {"py", "js", "ts", "html", "css", "java", "c", "cpp", "go", "rs", "sh", "ipynb"},
}
PARTIAL = ["*.crdownload", "*.part", "*.tmp", "*.download", "*.opdownload", "~*", ".*"]
FOLDER_NAMES = set(CATEGORIES) | {"Other"}


def category_of(path):
    ext = path.suffix.lstrip(".").lower()
    for name, extensions in CATEGORIES.items():
        if ext in extensions:
            return name
    return "Other"


def free_name(target):
    """target, or 'name (1).ext', 'name (2).ext'... so nothing is ever overwritten."""
    if not target.exists():
        return target
    number = 1
    while True:
        candidate = target.with_name(f"{target.stem} ({number}){target.suffix}")
        if not candidate.exists():
            return candidate
        number += 1


def plan(folder, settle, now=None):
    """Return ([(source, destination)], [(name, reason)]) for the files in the folder."""
    now = now if now is not None else time.time()
    moves, skipped = [], []
    for path in sorted(folder.iterdir()):
        if path.is_dir():
            continue
        if any(fnmatch.fnmatch(path.name, p) for p in PARTIAL):
            skipped.append((path.name, "download in progress or hidden"))
        elif now - path.stat().st_mtime < settle:
            skipped.append((path.name, "changed a moment ago; will wait"))
        else:
            moves.append((path, free_name(folder / category_of(path) / path.name)))
    return moves, skipped


def sort_once(folder, apply, settle, out=print):
    """Plan (and with apply, perform) one pass. Returns {category: count}."""
    moves, skipped = plan(folder, settle)
    counts = {}
    for source, target in moves:
        label = target.parent.name
        out(f"{source.name} -> {label}/" + (f" (as {target.name})" if target.name != source.name
                                            else ""))
        if apply:
            target.parent.mkdir(exist_ok=True)
            shutil.move(str(source), str(target))
        counts[label] = counts.get(label, 0) + 1
    for name, reason in skipped:
        out(f"skip {name}: {reason}")
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sort downloaded files into folders by type.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path.home() / "Downloads",
                        help="the folder to sort (your Downloads folder)")
    parser.add_argument("--watch", action="store_true", help="keep running and sort new files")
    parser.add_argument("--interval", type=float, default=10, help="seconds between passes (10)")
    parser.add_argument("--seconds", type=float, help="stop watching after this many seconds")
    parser.add_argument("--settle", type=float, default=5,
                        help="leave files alone that changed in the last N seconds (5)")
    parser.add_argument("--apply", action="store_true",
                        help="really move the files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    if args.interval <= 0 or args.settle < 0:
        parser.error("--interval must be above 0 and --settle can't be negative")

    total, started = {}, time.monotonic()
    try:
        while True:
            for label, number in sort_once(args.folder, args.apply, args.settle).items():
                total[label] = total.get(label, 0) + number
            if not args.watch or (args.seconds and time.monotonic() - started >= args.seconds):
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    moved = sum(total.values())
    summary = ", ".join(f"{n} {label}" for label, n in sorted(total.items())) or "nothing to sort"
    verb = "Moved" if args.apply else "Would move"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"\n{verb} {moved} file(s): {summary}.{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
