"""One-way sync: make a target folder match a source folder. Dry run by default."""
import argparse
import fnmatch
import hashlib
import os
import shutil
import sys
from pathlib import Path

MTIME_TOLERANCE = 2.0


def is_excluded(rel, patterns):
    parts = rel.split("/")
    return any(fnmatch.fnmatch(rel, p) or any(fnmatch.fnmatch(part, p) for part in parts)
               for p in patterns)


def list_files(root, patterns):
    """{relative posix path: Path} for the regular files below root, honouring excludes."""
    found = {}
    for current, dirnames, filenames in os.walk(root):
        here = Path(current)
        dirnames[:] = sorted(d for d in dirnames
                             if not is_excluded((here / d).relative_to(root).as_posix(), patterns)
                             and not (here / d).is_symlink())
        for name in filenames:
            path = here / name
            rel = path.relative_to(root).as_posix()
            if not is_excluded(rel, patterns) and not path.is_symlink():
                found[rel] = path
    return found


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def differs(source, target, quick):
    a, b = source.stat(), target.stat()
    if a.st_size != b.st_size:
        return True
    if quick:
        return a.st_mtime - b.st_mtime > MTIME_TOLERANCE  # source is newer
    return sha256(source) != sha256(target)


def make_plan(source_files, target_files, quick):
    """Return (to copy, to update, target-only) as sorted lists of relative paths."""
    new = sorted(r for r in source_files if r not in target_files)
    update = sorted(r for r in source_files if r in target_files
                    and differs(source_files[r], target_files[r], quick))
    extra = sorted(r for r in target_files if r not in source_files)
    return new, update, extra


def copy_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".sync-tmp")
    try:
        shutil.copy2(source, temp)
        os.replace(temp, target)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def prune_empty_dirs(root):
    for current, _dirs, _files in os.walk(root, topdown=False):
        path = Path(current)
        if path != root and not any(path.iterdir()):
            path.rmdir()


def main(argv=None):
    parser = argparse.ArgumentParser(description="One-way sync from SOURCE to TARGET.")
    parser.add_argument("source", type=Path, help="the folder to copy from (never changed)")
    parser.add_argument("target", type=Path, help="the folder that should end up matching it")
    parser.add_argument("--delete", action="store_true",
                        help="also remove files from TARGET that aren't in SOURCE")
    parser.add_argument("--quick", action="store_true",
                        help="compare size and modified time instead of file contents")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN")
    parser.add_argument("--allow-empty", action="store_true",
                        help="let --delete run even when SOURCE has no files")
    parser.add_argument("--apply", action="store_true", help="actually change the target")
    args = parser.parse_args(argv)
    if not args.source.is_dir():
        parser.error(f"not a folder: {args.source}")
    source, target = args.source.resolve(), args.target.resolve()
    if source == target or source in target.parents or target in source.parents:
        parser.error("the source and target folders can't contain each other")
    if args.target.exists() and not args.target.is_dir():
        parser.error(f"not a folder: {args.target}")

    try:
        source_files = list_files(source, args.exclude)
        target_files = list_files(target, args.exclude) if target.exists() else {}
        new, update, extra = make_plan(source_files, target_files, args.quick)
    except OSError as err:
        print(f"Couldn't read the folders: {err}", file=sys.stderr)
        return 1
    if args.delete and extra and not source_files and not args.allow_empty:
        print("The source has no files, so --delete would empty the target. "
              "Add --allow-empty if that's really what you want.")
        return 1

    print(f"{args.source} -> {args.target}: {len(new)} to add, {len(update)} to update, "
          f"{len(extra)} only in the target" + (" (to delete)." if args.delete else " (kept)."))
    for rel in new:
        print(f"  + {rel}")
    for rel in update:
        print(f"  ~ {rel}")
    for rel in extra:
        print(f"  {'-' if args.delete else '?'} {rel}")
    if not args.apply:
        print("\nDry run - nothing changed. Add --apply to sync.")
        return 0
    failed = 0
    for rel in new + update:
        try:
            copy_file(source_files[rel], target / rel)
        except OSError as err:
            failed += 1
            print(f"could not copy {rel}: {err}")
    if args.delete:
        for rel in extra:
            try:
                (target / rel).unlink()
            except OSError as err:
                failed += 1
                print(f"could not delete {rel}: {err}")
        prune_empty_dirs(target)
    print(f"\nSynced: {len(new) + len(update) - failed} file(s) copied"
          + (f", {len(extra)} deleted" if args.delete else "") + ".")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
