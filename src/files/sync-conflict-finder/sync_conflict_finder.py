"""Find sync-conflict copies left behind by Dropbox, OneDrive, Syncthing, Nextcloud and others."""
import argparse
import fnmatch
import hashlib
import os
import re
import sys
from pathlib import Path

ENDING = r"(?P<ext>\.[^./\\]+)?$"
CONFLICTED = re.compile(r"^(?P<base>.+?) \((?:[^()]*'s )?conflicted copy[^)]*\)" + ENDING,
                        re.IGNORECASE)
SYNCTHING = re.compile(r"^(?P<base>.+)\.sync-conflict-\d{8}-\d{6}(?:-\w+)?" + ENDING)
ONEDRIVE = re.compile(r"^(?P<base>.+)-(?P<host>[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)" + ENDING)
NUMBERED = re.compile(r"^(?P<base>.+?) \((?P<n>\d+)\)" + ENDING)


def human_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def is_excluded(rel, patterns):
    parts = rel.split("/")
    return any(fnmatch.fnmatch(rel, p) or any(fnmatch.fnmatch(part, p) for part in parts)
               for p in patterns)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(name, exists, loose=False):
    """Return (kind, original file name) if the name looks like a conflict copy, else None.

    `exists(name)` says whether a file with that name sits in the same folder; the OneDrive-style
    and numbered patterns are only believed when the original is really there.
    """
    for kind, pattern in (("Dropbox/Nextcloud conflicted copy", CONFLICTED),
                          ("Syncthing conflict", SYNCTHING)):
        match = pattern.match(name)
        if match:
            return kind, match.group("base") + (match.group("ext") or "")
    match = ONEDRIVE.match(name)
    if match and (any(c.isdigit() for c in match.group("host")) or len(match.group("host")) >= 6):
        original = match.group("base") + (match.group("ext") or "")
        if exists(original):
            return "OneDrive-style (computer name added)", original
    if loose:
        match = NUMBERED.match(name)
        if match:
            original = match.group("base") + (match.group("ext") or "")
            if exists(original):
                return "numbered copy, e.g. (1)", original
    return None


def find_conflicts(root, patterns, loose=False):
    found = []
    for current, dirnames, filenames in os.walk(root):
        here = Path(current)
        dirnames[:] = sorted(d for d in dirnames
                             if not is_excluded((here / d).relative_to(root).as_posix(), patterns)
                             and not (here / d).is_symlink())
        names = set(filenames)
        for name in sorted(filenames):
            rel = (here / name).relative_to(root).as_posix()
            if is_excluded(rel, patterns) or (here / name).is_symlink():
                continue
            hit = classify(name, names.__contains__, loose)
            if hit:
                found.append({"path": here / name, "rel": rel, "kind": hit[0],
                              "original": here / hit[1] if hit[1] in names else None,
                              "original_name": hit[1]})
    return found


def judge(conflict):
    """Describe how the conflict copy relates to its original."""
    path, original = conflict["path"], conflict["original"]
    if original is None:
        return "ORPHAN", "the original file is gone, so this copy may be the only one"
    a, b = path.stat(), original.stat()
    if a.st_size == b.st_size and sha256(path) == sha256(original):
        return "IDENTICAL", "same content as the original - safe to delete"
    newer = ("newer" if a.st_mtime - b.st_mtime > 1 else "older" if b.st_mtime - a.st_mtime > 1
             else "same age")
    return "DIFFERENT", (f"differs from the original ({human_size(a.st_size)} vs "
                         f"{human_size(b.st_size)}, copy is {newer}) - compare before deleting")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find sync-conflict copies in a folder.")
    parser.add_argument("folder", type=Path, help="the synced folder to scan")
    parser.add_argument("--loose", action="store_true",
                        help="also treat 'name (1).ext' as a conflict when 'name.ext' exists")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    try:
        conflicts = find_conflicts(args.folder, args.exclude, args.loose)
        verdicts = [judge(c) for c in conflicts]
    except OSError as err:
        print(f"Couldn't scan the folder: {err}", file=sys.stderr)
        return 1
    if not conflicts:
        print("No sync-conflict copies found.")
        return 0

    print(f"{len(conflicts)} conflict copy/copies found in {args.folder}:\n")
    for conflict, (label, why) in zip(conflicts, verdicts, strict=True):
        print(f"[{label}] {conflict['rel']}")
        print(f"    {conflict['kind']}; original: {conflict['original_name']}")
        print(f"    {why}")
    counts = {label: sum(v[0] == label for v in verdicts)
              for label in ("IDENTICAL", "DIFFERENT", "ORPHAN")}
    print(f"\n{counts['IDENTICAL']} identical, {counts['DIFFERENT']} different, "
          f"{counts['ORPHAN']} without an original. Nothing was changed or deleted.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
