"""Zip folders and files with exclude patterns. Dry run by default."""
import argparse
import fnmatch
import os
import sys
import zipfile
from pathlib import Path

COMMON_EXCLUDES = [".git", "node_modules", "__pycache__", "*.pyc", ".venv", "venv", ".idea",
                   ".DS_Store", "Thumbs.db"]


def human_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def is_excluded(rel, patterns):
    posix = rel.as_posix()
    return any(fnmatch.fnmatch(posix, p) or any(fnmatch.fnmatch(part, p) for part in rel.parts)
               for p in patterns)


def collect(source, patterns, skip, top_folder=True):
    """Return [(file path, name inside the zip)] for a folder or a single file."""
    if source.is_file():
        return [(source, source.name)]
    prefix = Path(source.name) if top_folder else Path()
    found = []
    for current, dirnames, filenames in os.walk(source):
        here = Path(current)
        dirnames[:] = sorted(d for d in dirnames
                             if not is_excluded((here / d).relative_to(source), patterns)
                             and not (here / d).is_symlink())
        for name in sorted(filenames):
            path = here / name
            rel = path.relative_to(source)
            if is_excluded(rel, patterns) or path.is_symlink() or path.resolve() in skip:
                continue
            found.append((path, (prefix / rel).as_posix()))
    return sorted(found, key=lambda entry: entry[1])


def write_zip(target, entries, level):
    partial = target.with_name(target.name + ".partial")
    try:
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED, compresslevel=level,
                             strict_timestamps=False) as archive:
            for path, name in entries:
                archive.write(path, name)
        partial.rename(target)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description="Zip folders with exclude patterns.")
    parser.add_argument("sources", nargs="+", type=Path, help="folders or files to zip")
    parser.add_argument("--out", type=Path, required=True, help="the .zip file to create")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                        help="leave out matching names or paths, e.g. '*.log' or build")
    parser.add_argument("--exclude-common", action="store_true",
                        help="also leave out .git, node_modules, __pycache__, .venv, .DS_Store...")
    parser.add_argument("--no-top-folder", action="store_true",
                        help="put a folder's contents at the top of the zip, not inside its name")
    parser.add_argument("--level", type=int, default=6, choices=range(1, 10), metavar="1-9",
                        help="compression level (6)")
    parser.add_argument("--apply", action="store_true", help="actually create the zip file")
    args = parser.parse_args(argv)
    for source in args.sources:
        if not source.exists():
            parser.error(f"not found: {source}")
    if args.out.suffix.lower() != ".zip":
        parser.error("--out should end in .zip")
    if args.out.exists():
        print(f"{args.out} already exists - pick a new name so nothing is overwritten.")
        return 1

    patterns = args.exclude + (COMMON_EXCLUDES if args.exclude_common else [])
    skip = {args.out.resolve(), args.out.resolve().with_name(args.out.name + ".partial")}
    entries = []
    for source in args.sources:
        entries += collect(source, patterns, skip, not args.no_top_folder)
    names = [name for _, name in entries]
    if len(set(names)) != len(names):
        print("Two files would get the same name inside the zip; "
              "remove --no-top-folder or rename a source.")
        return 1
    if not entries:
        print("Nothing to zip after the exclusions.")
        return 1
    total = sum(path.stat().st_size for path, _ in entries)
    print(f"{len(entries)} file(s), {human_size(total)} -> {args.out}")
    if not args.apply:
        for _, name in entries[:10]:
            print(f"  would add {name}")
        if len(entries) > 10:
            print(f"  ... and {len(entries) - 10} more")
        print("\nDry run - no zip created. Add --apply to create it.")
        return 0
    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        write_zip(args.out, entries, args.level)
    except OSError as err:
        print(f"Couldn't create the zip: {err}", file=sys.stderr)
        return 1
    packed = args.out.stat().st_size
    saved = 100 * (1 - packed / total) if total else 0
    print(f"Created {args.out}: {human_size(packed)} ({saved:.0f}% smaller).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
