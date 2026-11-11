"""Create compressed tar archives with a hash manifest, and verify or list them."""
import argparse
import fnmatch
import hashlib
import io
import json
import os
import sys
import tarfile
from datetime import datetime
from pathlib import Path

MANIFEST = "MANIFEST.json"
MODES = {".tar.gz": "gz", ".tgz": "gz", ".tar.bz2": "bz2", ".tar.xz": "xz", ".tar": ""}


def human_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def is_excluded(rel, patterns):
    parts = rel.split("/")
    return any(fnmatch.fnmatch(rel, p) or any(fnmatch.fnmatch(part, p) for part in parts)
               for p in patterns)


def compression_for(name):
    lowered = name.lower()
    for suffix, mode in MODES.items():
        if lowered.endswith(suffix):
            return mode
    raise ValueError("--out should end in .tar.gz, .tgz, .tar.bz2, .tar.xz or .tar")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect(sources, patterns):
    """Return [(path, name in the archive)] with each folder stored under its own name."""
    entries = []
    for source in sources:
        if source.is_file():
            entries.append((source, source.name))
            continue
        for current, dirnames, filenames in os.walk(source):
            here = Path(current)
            dirnames[:] = sorted(d for d in dirnames
                                 if not is_excluded((here / d).relative_to(source).as_posix(),
                                                    patterns) and not (here / d).is_symlink())
            for name in filenames:
                path = here / name
                rel = path.relative_to(source).as_posix()
                if not is_excluded(rel, patterns) and not path.is_symlink():
                    entries.append((path, f"{source.name}/{rel}"))
    return sorted(entries, key=lambda e: e[1])


def anonymise(info):
    """Don't record who owns the files; it's private and meaningless on another computer."""
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def create_archive(target, entries, now):
    manifest = {"created": now.isoformat(timespec="seconds"), "files": [
        {"path": name, "size": path.stat().st_size, "sha256": sha256(path)}
        for path, name in entries]}
    data = json.dumps(manifest, indent=1).encode("utf-8")
    partial = target.with_name(target.name + ".partial")
    mode = compression_for(target.name)
    try:
        with tarfile.open(partial, f"w:{mode}" if mode else "w") as tar:
            info = tarfile.TarInfo(MANIFEST)
            info.size, info.mtime = len(data), int(now.timestamp())
            tar.addfile(info, io.BytesIO(data))
            for path, name in entries:
                tar.add(path, arcname=name, recursive=False, filter=anonymise)
        partial.rename(target)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return manifest


def read_manifest(archive):
    with tarfile.open(archive) as tar:
        member = tar.extractfile(MANIFEST)
        if member is None:
            raise ValueError("no manifest inside the archive")
        return json.loads(member.read().decode("utf-8"))


def verify_archive(archive):
    """Return (checked count, missing, damaged, unlisted) comparing contents to the manifest."""
    manifest = read_manifest(archive)
    wanted = {f["path"]: f for f in manifest["files"]}
    damaged, seen = [], set()
    with tarfile.open(archive) as tar:
        for member in tar:
            if member.name == MANIFEST or not member.isfile():
                continue
            seen.add(member.name)
            entry = wanted.get(member.name)
            if entry is None:
                continue
            digest = hashlib.sha256()
            handle = tar.extractfile(member)
            for chunk in iter(lambda h=handle: h.read(1024 * 1024), b""):
                digest.update(chunk)
            if digest.hexdigest() != entry["sha256"] or member.size != entry["size"]:
                damaged.append(member.name)
    return (len(seen & set(wanted)), sorted(set(wanted) - seen), sorted(damaged),
            sorted(seen - set(wanted)))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Tar archives with a manifest.")
    parser.add_argument("action", choices=["create", "list", "verify"])
    parser.add_argument("paths", nargs="+", type=Path,
                        help="create: folders/files to archive; list and verify: the archive")
    parser.add_argument("--out", type=Path,
                        help="create: the archive to make (.tar.gz, .tar.xz...)")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN")
    parser.add_argument("--now", help="timestamp, YYYY-MM-DDTHH:MM:SS (for testing)")
    parser.add_argument("--apply", action="store_true", help="create: actually write the archive")
    args = parser.parse_args(argv)

    if args.action in ("list", "verify"):
        if len(args.paths) != 1 or not args.paths[0].is_file():
            parser.error(f"{args.action} needs exactly one archive file")
        try:
            if args.action == "list":
                manifest = read_manifest(args.paths[0])
                for f in manifest["files"]:
                    print(f"{f['size']:>10,}  {f['sha256'][:12]}  {f['path']}")
                total = sum(f["size"] for f in manifest["files"])
                print(f"{len(manifest['files'])} file(s), {human_size(total)}, "
                      f"created {manifest['created']}")
                return 0
            checked, missing, damaged, unlisted = verify_archive(args.paths[0])
        except (OSError, tarfile.TarError, ValueError, KeyError, json.JSONDecodeError) as err:
            print(f"Couldn't read the archive: {err}", file=sys.stderr)
            return 1
        print(f"Checked {checked} file(s) against the manifest.")
        groups = (("Missing", missing), ("Damaged", damaged), ("Not in manifest", unlisted))
        for title, items in groups:
            if items:
                print(f"{title} ({len(items)}): " + ", ".join(items[:10]))
        if missing or damaged:
            print("PROBLEMS FOUND - the archive is damaged or incomplete.")
            return 1
        print("OK - every file matches its recorded hash.")
        return 0

    if not args.out:
        parser.error("create needs --out ARCHIVE")
    for source in args.paths:
        if not source.exists():
            parser.error(f"not found: {source}")
    try:
        compression_for(args.out.name)
        now = datetime.fromisoformat(args.now) if args.now else datetime.now()
    except ValueError as err:
        parser.error(str(err))
    if args.out.exists():
        print(f"{args.out} already exists - pick a new name so nothing is overwritten.")
        return 1
    skip = args.out.resolve()
    entries = [(p, n) for p, n in collect(args.paths, args.exclude) if p.resolve() != skip]
    names = [n for _, n in entries]
    if len(set(names)) != len(names):
        print("Two files would get the same name inside the archive; rename a source.")
        return 1
    if not entries:
        print("Nothing to archive after the exclusions.")
        return 1
    total = sum(p.stat().st_size for p, _ in entries)
    print(f"{len(entries)} file(s), {human_size(total)} -> {args.out} (plus {MANIFEST})")
    if not args.apply:
        for _, name in entries[:10]:
            print(f"  would add {name}")
        if len(entries) > 10:
            print(f"  ... and {len(entries) - 10} more")
        print("\nDry run - no archive created. Add --apply to create it.")
        return 0
    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        create_archive(args.out, entries, now)
    except OSError as err:
        print(f"Couldn't create the archive: {err}", file=sys.stderr)
        return 1
    size = args.out.stat().st_size
    saved = 100 * (1 - size / total) if total else 0
    print(f"Created {args.out}: {human_size(size)} ({saved:.0f}% smaller). "
          "Check it any time with: verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
