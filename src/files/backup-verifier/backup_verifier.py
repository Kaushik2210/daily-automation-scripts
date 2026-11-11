"""Verify a backup (a folder or a .zip) against its source by comparing file hashes."""
import argparse
import fnmatch
import hashlib
import os
import sys
import zipfile
from pathlib import Path

META = [".backup-manifest.json", ".history"]  # files that incremental-backup adds to a backup


def is_excluded(rel, patterns):
    parts = rel.split("/")
    return any(fnmatch.fnmatch(rel, p) or any(fnmatch.fnmatch(part, p) for part in parts)
               for p in patterns)


def hash_stream(handle):
    digest = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def read_folder(folder, patterns, quick):
    """Return {relative path: (size, hash or None)} for a folder."""
    found = {}
    for current, dirnames, filenames in os.walk(folder):
        here = Path(current)
        dirnames[:] = sorted(d for d in dirnames
                             if not is_excluded((here / d).relative_to(folder).as_posix(), patterns)
                             and not (here / d).is_symlink())
        for name in filenames:
            path = here / name
            rel = path.relative_to(folder).as_posix()
            if is_excluded(rel, patterns) or path.is_symlink():
                continue
            if quick:
                found[rel] = (path.stat().st_size, None)
            else:
                with path.open("rb") as handle:
                    found[rel] = (path.stat().st_size, hash_stream(handle))
    return found


def read_zip(archive, patterns, quick, strip=None):
    """Same as read_folder for a zip; a single top-level folder in the zip is stripped."""
    found = {}
    with zipfile.ZipFile(archive) as z:
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        tops = {n.split("/", 1)[0] for n in names if "/" in n}
        prefix = strip if strip is not None else (
            tops.pop() + "/" if len(tops) == 1 and all("/" in n for n in names) else "")
        for info in z.infolist():
            if info.is_dir():
                continue
            rel = info.filename.removeprefix(prefix)
            if is_excluded(rel, patterns):
                continue
            if quick:
                found[rel] = (info.file_size, None)
            else:
                with z.open(info) as handle:
                    found[rel] = (info.file_size, hash_stream(handle))
    return found


def compare(source, backup):
    """Return (missing, different, extra) sorted lists of relative paths."""
    missing = sorted(p for p in source if p not in backup)
    extra = sorted(p for p in backup if p not in source)
    different = sorted(p for p in source if p in backup and source[p] != backup[p])
    return missing, different, extra


def show(title, items, limit=20):
    if not items:
        return
    print(f"{title} ({len(items)}):")
    for item in items[:limit]:
        print(f"  {item}")
    if len(items) > limit:
        print(f"  ... and {len(items) - limit} more")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify a backup against its source.")
    parser.add_argument("source", type=Path, help="the original folder")
    parser.add_argument("backup", type=Path, help="the backup: a folder or a .zip file")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                        help="ignore matching names or paths on both sides")
    parser.add_argument("--quick", action="store_true",
                        help="compare file sizes only (fast, but won't catch same-size changes)")
    parser.add_argument("--strict", action="store_true",
                        help="also fail when the backup has files the source doesn't")
    parser.add_argument("--strip", help="folder prefix to remove from names inside a zip")
    args = parser.parse_args(argv)
    if not args.source.is_dir():
        parser.error(f"not a folder: {args.source}")
    if not args.backup.exists():
        parser.error(f"not found: {args.backup}")
    patterns = args.exclude + META

    try:
        source = read_folder(args.source, args.exclude, args.quick)
        if args.backup.is_file():
            backup = read_zip(args.backup, patterns, args.quick, args.strip)
        else:
            backup = read_folder(args.backup, patterns, args.quick)
    except (OSError, zipfile.BadZipFile) as err:
        print(f"Couldn't read the files: {err}", file=sys.stderr)
        return 1

    missing, different, extra = compare(source, backup)
    how = "by size" if args.quick else "by SHA-256"
    print(f"Compared {len(source)} source file(s) with {len(backup)} in the backup {how}.")
    show("Missing from the backup", missing)
    show("Different in the backup", different)
    show("Only in the backup", extra)
    bad = len(missing) + len(different) + (len(extra) if args.strict else 0)
    if not (missing or different or extra):
        print("OK - the backup matches the source exactly.")
    elif not bad:
        print("OK - every source file is in the backup (it also has extra files).")
    else:
        print("PROBLEMS FOUND - this backup can't be trusted yet.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
