"""Copy folders into a timestamped backup folder. Dry run by default."""
import argparse
import fnmatch
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


def human_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def is_excluded(rel, patterns):
    """True if the relative path (or any folder or file name in it) matches an exclude pattern."""
    posix = rel.as_posix()
    return any(fnmatch.fnmatch(posix, p) or any(fnmatch.fnmatch(part, p) for part in rel.parts)
               for p in patterns)


def scan(source, patterns):
    """Return (files, empty dirs, skipped count, total bytes). Paths are relative to source."""
    files, folders, skipped, total = [], [], 0, 0
    for current, dirnames, filenames in os.walk(source):
        here = Path(current)
        keep = []
        for name in sorted(dirnames):
            rel = (here / name).relative_to(source)
            if is_excluded(rel, patterns) or (here / name).is_symlink():
                skipped += 1  # excluded, or a link that could point outside the folder
            else:
                keep.append(name)
        dirnames[:] = keep  # don't walk into skipped folders
        if not keep and not filenames and here != source:
            folders.append(here.relative_to(source))
        for name in sorted(filenames):
            rel = (here / name).relative_to(source)
            if is_excluded(rel, patterns) or (here / name).is_symlink():
                skipped += 1
            else:
                files.append(rel)
                total += (here / name).stat().st_size
    return sorted(files), sorted(folders), skipped, total


def backup_name(source, now):
    return f"{source.name or 'backup'}-{now:%Y%m%d-%H%M%S}"


def copy_tree(source, target, files, folders):
    """Copy into a '.partial' folder first so a failed run never leaves a half-made backup."""
    partial = target.with_name(target.name + ".partial")
    if partial.exists():
        shutil.rmtree(partial)
    partial.mkdir(parents=True)
    try:
        for rel in folders:
            (partial / rel).mkdir(parents=True, exist_ok=True)
        for rel in files:
            (partial / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / rel, partial / rel)
            if (partial / rel).stat().st_size != (source / rel).stat().st_size:
                raise OSError(f"size mismatch after copying {rel}")
        partial.rename(target)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description="Copy folders to a timestamped backup folder.")
    parser.add_argument("sources", nargs="+", type=Path, help="folders to back up")
    parser.add_argument("--dest", type=Path, required=True, help="where backups are collected")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                        help="skip matching files or folders, e.g. node_modules or '*.tmp'")
    parser.add_argument("--now", help="timestamp to use, YYYY-MM-DDTHH:MM:SS (for testing)")
    parser.add_argument("--apply", action="store_true", help="actually make the backup")
    args = parser.parse_args(argv)
    try:
        now = datetime.fromisoformat(args.now) if args.now else datetime.now()
    except ValueError:
        parser.error("--now must look like 2026-11-10T09:00:00")

    dest, problems = args.dest.resolve(), 0
    for source in args.sources:
        if not source.is_dir():
            print(f"{source}: not a folder, skipped")
            problems += 1
            continue
        real = source.resolve()
        if dest == real or real in dest.parents:
            print(f"{source}: the backup folder can't be inside the folder being backed up")
            problems += 1
            continue
        target = dest / backup_name(real, now)
        files, folders, skipped, total = scan(real, args.exclude)
        print(f"{source} -> {target}\n  {len(files)} file(s), {human_size(total)}"
              + (f", {skipped} skipped" if skipped else ""))
        if target.exists():
            print("  that backup folder already exists - wait a second or change --now")
            problems += 1
        elif not args.apply:
            for rel in files[:8]:
                print(f"    would copy {rel.as_posix()}")
            if len(files) > 8:
                print(f"    ... and {len(files) - 8} more")
        else:
            try:
                copy_tree(real, target, files, folders)
                print("  done")
            except OSError as err:
                print(f"  failed: {err}")
                problems += 1
    if not args.apply:
        print("\nDry run - nothing copied. Add --apply to make the backup.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
