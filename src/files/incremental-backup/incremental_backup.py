"""Back up only the files that are new or changed since the last run. Dry run by default."""
import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

MANIFEST = ".backup-manifest.json"
HISTORY = ".history"
MTIME_TOLERANCE = 2.0  # FAT and some cloud drives only keep time to the nearest 2 seconds


def human_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def is_excluded(rel, patterns):
    posix = rel.as_posix()
    return any(fnmatch.fnmatch(posix, p) or any(fnmatch.fnmatch(part, p) for part in rel.parts)
               for p in patterns)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan(source, patterns, use_hash=False):
    """Return {relative path: {size, mtime[, sha256]}} for every regular file in source."""
    found = {}
    for current, dirnames, filenames in os.walk(source):
        here = Path(current)
        dirnames[:] = sorted(d for d in dirnames if not is_excluded((here / d).relative_to(source),
                                                                      patterns)
                             and not (here / d).is_symlink())
        for name in sorted(filenames):
            path = here / name
            rel = path.relative_to(source)
            if is_excluded(rel, patterns) or path.is_symlink():
                continue
            info = path.stat()
            entry = {"size": info.st_size, "mtime": round(info.st_mtime, 3)}
            if use_hash:
                entry["sha256"] = sha256(path)
            found[rel.as_posix()] = entry
    return found


def load_manifest(dest):
    path = dest / MANIFEST
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("files", {})


def plan(current, previous, dest, use_hash=False):
    """Return (new, changed, removed) lists of relative paths."""
    new, changed = [], []
    for rel, now in current.items():
        before = previous.get(rel)
        if before is None or not (dest / rel).is_file():
            new.append(rel)
        elif use_hash and "sha256" in before and "sha256" in now:
            if before["sha256"] != now["sha256"]:
                changed.append(rel)
        elif before["size"] != now["size"] or abs(before["mtime"] - now["mtime"]) > MTIME_TOLERANCE:
            changed.append(rel)
    removed = sorted(rel for rel in previous if rel not in current)
    return new, changed, removed


def apply_plan(source, dest, current, new, changed, stamp, keep_history):
    for rel in new + changed:
        target = dest / rel
        if keep_history and target.exists():  # never silently overwrite an older backup
            old = dest / HISTORY / stamp / rel
            old.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(old))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, target)
    manifest = {"source": str(source), "updated": stamp, "files": current}
    (dest / MANIFEST).write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Incremental backup of one folder.")
    parser.add_argument("source", type=Path, help="the folder to back up")
    parser.add_argument("--dest", type=Path, required=True, help="the backup folder (a mirror)")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN")
    parser.add_argument("--hash", action="store_true",
                        help="detect changes by content, not size and time (slower, exact)")
    parser.add_argument("--no-history", action="store_true",
                        help="overwrite changed files without keeping the old version")
    parser.add_argument("--now", help="timestamp, YYYY-MM-DDTHH:MM:SS (for testing)")
    parser.add_argument("--apply", action="store_true", help="actually copy the files")
    args = parser.parse_args(argv)
    if not args.source.is_dir():
        parser.error(f"not a folder: {args.source}")
    source, dest = args.source.resolve(), args.dest.resolve()
    if dest == source or source in dest.parents or dest in source.parents:
        parser.error("the source and backup folders can't contain each other")
    try:
        stamp = (datetime.fromisoformat(args.now) if args.now else datetime.now()
                 ).strftime("%Y%m%d-%H%M%S")
        previous = load_manifest(dest)
    except (ValueError, json.JSONDecodeError, OSError) as err:
        print(f"Couldn't read the previous backup record: {err}", file=sys.stderr)
        return 1

    current = scan(source, args.exclude, args.hash)
    new, changed, removed = plan(current, previous, dest, args.hash)
    size = sum(current[rel]["size"] for rel in new + changed)
    print(f"{len(current)} file(s) in {args.source}: {len(new)} new, {len(changed)} changed, "
          f"{len(current) - len(new) - len(changed)} unchanged ({human_size(size)} to copy).")
    if removed:
        print(f"{len(removed)} file(s) were removed from the source; their backups are kept.")
    for rel in new:
        print(f"  + {rel}")
    for rel in changed:
        print(f"  ~ {rel}")
    if not args.apply:
        print("\nDry run - nothing copied. Add --apply to back up these files.")
        return 0
    if not (new or changed) and (dest / MANIFEST).is_file():
        print("\nNothing to do.")
        return 0
    try:
        dest.mkdir(parents=True, exist_ok=True)
        apply_plan(source, dest, current, new, changed, stamp, not args.no_history)
    except OSError as err:
        print(f"\nCopy failed: {err}", file=sys.stderr)
        return 1
    print(f"\nCopied {len(new) + len(changed)} file(s) to {args.dest}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
