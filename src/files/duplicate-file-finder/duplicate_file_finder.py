"""Find duplicate files by size first, then by SHA-256 content hash."""
import argparse
import hashlib
import sys
from collections import defaultdict
from pathlib import Path


def file_hash(path, chunk=1024 * 1024):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def find_duplicates(root, min_size=1):
    """Return a list of groups; each group is a list of paths with identical content."""
    by_size = defaultdict(list)
    for path in Path(root).rglob("*"):
        if path.is_file() and not path.is_symlink():
            size = path.stat().st_size
            if size >= min_size:
                by_size[size].append(path)

    groups = []
    for paths in by_size.values():
        if len(paths) < 2:
            continue
        by_hash = defaultdict(list)
        for path in paths:
            try:
                by_hash[file_hash(path)].append(path)
            except OSError as err:
                print(f"skipped {path}: {err}", file=sys.stderr)
        groups.extend(sorted(g) for g in by_hash.values() if len(g) > 1)
    return sorted(groups)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find duplicate files under a folder.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--min-size", type=int, default=1, help="ignore files smaller than N bytes")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    groups = find_duplicates(args.folder, args.min_size)
    wasted = 0
    for number, group in enumerate(groups, 1):
        size = group[0].stat().st_size
        wasted += size * (len(group) - 1)
        print(f"Group {number} ({size} bytes each):")
        for path in group:
            print(f"  {path}")
    print(f"{len(groups)} duplicate group(s), {wasted} bytes could be reclaimed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
