"""Write a checksum list for a folder, then verify the folder against it later."""
import argparse
import hashlib
import sys
from pathlib import Path

DEFAULT_NAME = "SHA256SUMS.txt"


def sha256_of(path, chunk=1024 * 1024):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def scan(folder, skip=()):
    """Return {relative_posix_path: sha256} for every file under `folder`."""
    folder = Path(folder)
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.name not in skip:
            result[path.relative_to(folder).as_posix()] = sha256_of(path)
    return result


def write_manifest(hashes):
    return "".join(f"{digest}  {name}\n" for name, digest in sorted(hashes.items()))


def read_manifest(text):
    hashes = {}
    for line in text.splitlines():
        digest, _, name = line.partition("  ")
        if digest and name:
            hashes[name] = digest
    return hashes


def compare(recorded, current):
    """Return (changed, missing, new) lists of file names."""
    changed = sorted(n for n in recorded if n in current and recorded[n] != current[n])
    missing = sorted(n for n in recorded if n not in current)
    new = sorted(n for n in current if n not in recorded)
    return changed, missing, new


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create or verify a folder checksum manifest.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--manifest", type=Path,
                        help=f"manifest file (default: <folder>/{DEFAULT_NAME})")
    parser.add_argument("--verify", action="store_true",
                        help="check the folder against the manifest instead of creating one")
    parser.add_argument("--apply", action="store_true",
                        help="really write the manifest (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    manifest = args.manifest or args.folder / DEFAULT_NAME

    current = scan(args.folder, skip={manifest.name})
    if args.verify:
        if not manifest.is_file():
            parser.error(f"manifest not found: {manifest}")
        recorded = read_manifest(manifest.read_text(encoding="utf-8"))
        changed, missing, new = compare(recorded, current)
        for label, names in (("CHANGED", changed), ("MISSING", missing), ("NEW", new)):
            for name in names:
                print(f"{label:<8}{name}")
        problems = len(changed) + len(missing)
        print(f"{len(current)} file(s) checked: {len(changed)} changed, {len(missing)} missing, "
              f"{len(new)} new.")
        return 1 if problems else 0

    print(f"{len(current)} file(s) would be listed in {manifest}.")
    if args.apply:
        manifest.write_text(write_manifest(current), encoding="utf-8")
        print(f"Wrote {manifest}.")
    else:
        print("Dry run: nothing written. Use --apply to do it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
