"""Estimate how big a backup will be, and whether it fits, before you run it. Read-only."""
import argparse
import contextlib
import fnmatch
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

TEXTLIKE = {".txt", ".md", ".py", ".js", ".ts", ".json", ".csv", ".html", ".css", ".xml", ".log",
            ".yml", ".yaml", ".sql", ".c", ".h", ".cpp", ".java", ".go", ".rs", ".sh", ".ini",
            ".toml", ".tsv", ".svg", ".rtf", ".tex"}
PACKED = {".zip", ".gz", ".bz2", ".xz", ".7z", ".rar", ".jpg", ".jpeg", ".png", ".gif", ".webp",
          ".heic", ".mp3", ".mp4", ".mkv", ".avi", ".mov", ".m4a", ".flac", ".docx", ".xlsx",
          ".pptx", ".pdf", ".iso", ".whl", ".jar", ".apk", ".woff2"}
RATIOS = {"text": 0.25, "packed": 1.0, "other": 0.7}


def human_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def is_excluded(rel, patterns):
    parts = rel.split("/")
    return any(fnmatch.fnmatch(rel, p) or any(fnmatch.fnmatch(part, p) for part in parts)
               for p in patterns)


def kind_of(path):
    ext = path.suffix.lower()
    return "text" if ext in TEXTLIKE else "packed" if ext in PACKED else "other"


def scan(root, patterns):
    """Return (files as [(relative path, size)], skipped count, skipped bytes, folder count)."""
    files, skipped, skipped_bytes, folders = [], 0, 0, 0
    for current, dirnames, filenames in os.walk(root):
        here = Path(current)
        keep = []
        for name in sorted(dirnames):
            rel = (here / name).relative_to(root).as_posix()
            if is_excluded(rel, patterns) or (here / name).is_symlink():
                skipped += 1
                skipped_bytes += tree_size(here / name)
            else:
                keep.append(name)
        dirnames[:] = keep
        folders += len(keep)
        for name in filenames:
            path = here / name
            rel = path.relative_to(root).as_posix()
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if is_excluded(rel, patterns) or path.is_symlink():
                skipped += 1
                skipped_bytes += size
            else:
                files.append((rel, size))
    return files, skipped, skipped_bytes, folders


def tree_size(path):
    if path.is_symlink():
        return 0
    total = 0
    for current, _dirs, filenames in os.walk(path):
        for name in filenames:
            with contextlib.suppress(OSError):
                total += (Path(current) / name).stat().st_size
    return total


def estimate(files):
    """Return (raw bytes, estimated compressed bytes, bytes per category)."""
    per_kind = Counter()
    for rel, size in files:
        per_kind[kind_of(Path(rel))] += size
    packed = sum(size * RATIOS[kind] for kind, size in per_kind.items())
    return sum(per_kind.values()), int(packed), dict(per_kind)


def free_space(dest):
    probe = dest
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        return shutil.disk_usage(probe).free
    except OSError:
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Estimate backup size before you run it.")
    parser.add_argument("folders", nargs="+", type=Path, help="the folders you plan to back up")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN")
    parser.add_argument("--dest", type=Path, help="where the backup will go, to check free space")
    parser.add_argument("--top", type=int, default=5, help="how many biggest files to list (5)")
    args = parser.parse_args(argv)
    for folder in args.folders:
        if not folder.is_dir():
            parser.error(f"not a folder: {folder}")

    all_files, skipped, skipped_bytes, folders = [], 0, 0, 0
    for folder in args.folders:
        files, skip, skip_bytes, count = scan(folder, args.exclude)
        label = folder.name or str(folder)
        all_files += [(f"{label}/{rel}", size) for rel, size in files]
        skipped += skip
        skipped_bytes += skip_bytes
        folders += count
    if not all_files:
        print("There is nothing to back up (no files after the exclusions).")
        return 1

    raw, packed, per_kind = estimate(all_files)
    print(f"{len(all_files):,} file(s) in {folders:,} folder(s): {human_size(raw)}")
    if skipped:
        print(f"Excluded {skipped:,} item(s) worth {human_size(skipped_bytes)}.")
    print(f"A plain copy needs about {human_size(raw)}; a compressed archive about "
          f"{human_size(packed)} (a rough estimate).")

    top_dirs = Counter()
    for rel, size in all_files:
        top_dirs["/".join(rel.split("/")[:2]) if rel.count("/") > 1 else rel.split("/")[0]] += size
    print("\nBiggest folders:")
    for name, size in top_dirs.most_common(5):
        print(f"  {human_size(size):>10}  {name}")
    print("\nBiggest files:")
    for rel, size in sorted(all_files, key=lambda f: -f[1])[:max(args.top, 1)]:
        print(f"  {human_size(size):>10}  {rel}")
    kinds = Counter()
    for rel, size in all_files:
        kinds[Path(rel).suffix.lower() or "(none)"] += size
    print("\nBy file type: " + ", ".join(f"{ext} {human_size(size)}"
                                          for ext, size in kinds.most_common(6)))

    if args.dest:
        free = free_space(args.dest.resolve())
        if free is None:
            print("\nCouldn't read the free space at the destination.")
        else:
            verdict = ("fits" if raw <= free else "fits only if compressed" if packed <= free
                       else "does NOT fit")
            print(f"\nFree space at {args.dest}: {human_size(free)} - the backup {verdict}.")
            return 0 if raw <= free or packed <= free else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
