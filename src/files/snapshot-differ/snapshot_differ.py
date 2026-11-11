"""Take snapshots of folders and compare them: what was added, removed, changed or moved."""
import argparse
import fnmatch
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def human_size(size):
    sign = "-" if size < 0 else ""
    size = abs(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{sign}{size} B" if unit == "B" else f"{sign}{size:.1f} {unit}"
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


def take_snapshot(folder, patterns, quick=False, created=None):
    """Describe every file in a folder: size and (unless quick) a SHA-256 of its content."""
    files = {}
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
            entry = {"size": path.stat().st_size}
            if not quick:
                entry["sha256"] = sha256(path)
            files[rel] = entry
    stamp = (created or datetime.now()).isoformat(timespec="seconds")
    return {"root": folder.name, "created": stamp, "files": dict(sorted(files.items()))}


def load_snapshot(source, patterns, quick):
    """A snapshot from a saved .json manifest, or taken now from a folder."""
    if source.is_dir():
        return take_snapshot(source.resolve(), patterns, quick)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data.get("files"), dict):
        raise ValueError(f"{source.name} isn't a snapshot file")
    return data


def compare(old, new):
    """Return a dict with added, removed, changed, moved ([(old, new)]) and unchanged counts."""
    a, b = old["files"], new["files"]
    added = sorted(p for p in b if p not in a)
    removed = sorted(p for p in a if p not in b)
    changed = []
    for path in sorted(set(a) & set(b)):
        if a[path].get("sha256") and b[path].get("sha256"):
            if a[path]["sha256"] != b[path]["sha256"]:
                changed.append(path)
        elif a[path]["size"] != b[path]["size"]:
            changed.append(path)
    moved, by_hash = [], {}
    for path in removed:
        if a[path].get("sha256"):
            by_hash.setdefault(a[path]["sha256"], []).append(path)
    for path in list(added):
        candidates = by_hash.get(b[path].get("sha256") or "", [])
        if candidates:
            old_path = candidates.pop(0)
            moved.append((old_path, path))
            added.remove(path)
            removed.remove(old_path)
    return {"added": added, "removed": removed, "changed": changed, "moved": sorted(moved),
            "unchanged": len(set(a) & set(b)) - len(changed)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Snapshot folders and compare snapshots.")
    parser.add_argument("action", choices=["compare", "snapshot"])
    parser.add_argument("paths", nargs="+", type=Path,
                        help="compare: OLD and NEW (folders or snapshot .json files); "
                             "snapshot: the folder to describe")
    parser.add_argument("--out", type=Path, help="snapshot: new .json file to write")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN")
    parser.add_argument("--quick", action="store_true",
                        help="record sizes only, no hashes (fast; misses same-size edits)")
    args = parser.parse_args(argv)

    if args.action == "snapshot":
        if len(args.paths) != 1 or not args.paths[0].is_dir():
            parser.error("snapshot needs exactly one folder")
        if not args.out:
            parser.error("snapshot needs --out FILE")
        if args.out.exists():
            print(f"{args.out} already exists - pick a new name so nothing is overwritten.")
            return 1
        snap = take_snapshot(args.paths[0].resolve(), args.exclude, args.quick)
        args.out.write_text(json.dumps(snap, indent=1) + "\n", encoding="utf-8")
        total = sum(f["size"] for f in snap["files"].values())
        print(f"Saved a snapshot of {len(snap['files'])} file(s), {human_size(total)}, "
              f"to {args.out}.")
        return 0

    if len(args.paths) != 2:
        parser.error("compare needs exactly two paths: OLD and NEW")
    try:
        old, new = (load_snapshot(p, args.exclude, args.quick) for p in args.paths)
    except (OSError, ValueError, json.JSONDecodeError) as err:
        print(f"Couldn't read a snapshot: {err}", file=sys.stderr)
        return 1

    result = compare(old, new)
    delta = (sum(f["size"] for f in new["files"].values())
             - sum(f["size"] for f in old["files"].values()))
    print(f"OLD: {len(old['files'])} file(s) ({old.get('created', '?')})   "
          f"NEW: {len(new['files'])} file(s) ({new.get('created', '?')})")
    for label, key, mark in (("Added", "added", "+"), ("Removed", "removed", "-"),
                             ("Changed", "changed", "~")):
        if result[key]:
            print(f"{label} ({len(result[key])}):")
            print("\n".join(f"  {mark} {p}" for p in result[key]))
    if result["moved"]:
        print(f"Moved or renamed ({len(result['moved'])}):")
        print("\n".join(f"  > {a} -> {b}" for a, b in result["moved"]))
    differences = sum(len(result[k]) for k in ("added", "removed", "changed", "moved"))
    print(f"{result['unchanged']} unchanged. Size change: {human_size(delta)}.")
    if not differences:
        print("The snapshots are identical.")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())
