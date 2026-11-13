"""Detect changed, added and removed files against a stored baseline (a file integrity monitor)."""
import argparse
import fnmatch
import hashlib
import hmac
import json
import os
import stat
import sys
from datetime import datetime
from pathlib import Path


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


def scan(folder, patterns):
    """Describe every regular file below folder: size, SHA-256 and (on POSIX) permissions."""
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
            info = path.stat()
            entry = {"size": info.st_size, "sha256": sha256(path)}
            if os.name == "posix":
                entry["mode"] = format(stat.S_IMODE(info.st_mode), "04o")
            files[rel] = entry
    return dict(sorted(files.items()))


def sign(files, key):
    payload = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(key.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def compare(baseline, current):
    """Return (modified, added, removed, permission-only changes)."""
    modified = sorted(p for p in baseline if p in current
                      and baseline[p]["sha256"] != current[p]["sha256"])
    added = sorted(p for p in current if p not in baseline)
    removed = sorted(p for p in baseline if p not in current)
    perms = sorted(p for p in baseline if p in current and p not in modified
                   and baseline[p].get("mode") and current[p].get("mode")
                   and baseline[p]["mode"] != current[p]["mode"])
    return modified, added, removed, perms


def make_baseline(folder, files, key):
    data = {"version": 1, "created": datetime.now().isoformat(timespec="seconds"),
            "root": folder.name, "algorithm": "sha256", "files": files}
    if key:
        data["hmac"] = sign(files, key)
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description="File integrity monitor.")
    parser.add_argument("action", choices=["init", "check", "update"],
                        help="init: record a baseline; check: compare; update: accept changes")
    parser.add_argument("folder", type=Path, help="the folder to watch")
    parser.add_argument("--baseline", type=Path, required=True, help="the baseline JSON file")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN")
    parser.add_argument("--key-env", metavar="VAR",
                        help="name of an environment variable holding a secret used to sign the "
                             "baseline, so tampering with the baseline itself is detected")
    parser.add_argument("--apply", action="store_true",
                        help="update: actually rewrite the baseline")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    key = os.environ.get(args.key_env) if args.key_env else None
    if args.key_env and not key:
        parser.error(f"the environment variable {args.key_env} is empty or not set")
    folder = args.folder.resolve()

    try:
        current = scan(folder, args.exclude)
    except OSError as err:
        print(f"Couldn't read the folder: {err.strerror or err}", file=sys.stderr)
        return 1

    if args.action == "init":
        if args.baseline.exists():
            print(f"{args.baseline} already exists - use 'update' to refresh it.")
            return 1
        args.baseline.write_text(json.dumps(make_baseline(folder, current, key), indent=1) + "\n",
                                 encoding="utf-8")
        print(f"Recorded {len(current)} file(s) in {args.baseline}"
              + (" (signed)." if key else ". Keep this file somewhere safe."))
        return 0

    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        recorded = baseline["files"]
    except (OSError, ValueError, KeyError, TypeError) as err:
        print(f"Couldn't read the baseline {args.baseline}: {err}", file=sys.stderr)
        return 1
    if baseline.get("hmac"):
        if not key:
            print("Note: this baseline is signed; pass --key-env to verify it hasn't been altered.")
        elif not hmac.compare_digest(baseline["hmac"], sign(recorded, key)):
            print("BASELINE TAMPERED: its signature doesn't match, so it can't be trusted.")
            return 2

    modified, added, removed, perms = compare(recorded, current)
    changes = len(modified) + len(added) + len(removed) + len(perms)
    print(f"Compared {len(current)} file(s) with the baseline of {baseline.get('created', '?')}: "
          f"{len(recorded) - len(removed) - len(modified)} unchanged.")
    for title, items in (("MODIFIED", modified), ("ADDED", added), ("REMOVED", removed),
                         ("PERMISSIONS CHANGED", perms)):
        for rel in items:
            print(f"  {title:<19} {rel}")
    if args.action == "check":
        print("No changes - everything matches." if not changes
              else f"{changes} change(s) found.")
        return 1 if changes else 0

    if not changes:
        print("The baseline is already up to date.")
        return 0
    if not args.apply:
        print("\nDry run - baseline not changed. Add --apply to accept these changes.")
        return 0
    backup = args.baseline.with_name(
        f"{args.baseline.name}.{datetime.now():%Y%m%d-%H%M%S}.prev")
    backup.write_text(args.baseline.read_text(encoding="utf-8"), encoding="utf-8")
    args.baseline.write_text(json.dumps(make_baseline(folder, current, key), indent=1) + "\n",
                             encoding="utf-8")
    print(f"\nBaseline updated. The previous one was kept as {backup.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
