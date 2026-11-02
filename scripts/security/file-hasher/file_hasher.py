"""Print MD5, SHA-1, SHA-256 (and more) hashes for files in one read."""
import argparse
import hashlib
import sys
from pathlib import Path

ALGORITHMS = ["md5", "sha1", "sha256", "sha512"]


def hash_file(path, algorithms, chunk=1024 * 1024):
    """Return {algorithm: hexdigest}, reading the file once."""
    digests = {name: hashlib.new(name) for name in algorithms}
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            for digest in digests.values():
                digest.update(block)
    return {name: digest.hexdigest() for name, digest in digests.items()}


def collect(paths, recursive):
    files = []
    for path in paths:
        if path.is_dir():
            pattern = "**/*" if recursive else "*"
            files.extend(sorted(p for p in path.glob(pattern) if p.is_file()))
        else:
            files.append(path)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Hash files with one or more algorithms.")
    parser.add_argument("paths", nargs="+", type=Path, help="files or folders")
    parser.add_argument("-a", "--algorithm", action="append", choices=ALGORITHMS,
                        help="algorithm to use (repeatable; default: sha256)")
    parser.add_argument("-r", "--recursive", action="store_true", help="include subfolders")
    parser.add_argument("--sums", action="store_true",
                        help="print in sha256sum style ('hash  file') for a single algorithm")
    args = parser.parse_args(argv)
    algorithms = args.algorithm or ["sha256"]
    if args.sums and len(algorithms) != 1:
        parser.error("--sums needs exactly one algorithm")

    status = 0
    for path in collect(args.paths, args.recursive):
        try:
            hashes = hash_file(path, algorithms)
        except OSError as err:
            print(f"{path}: {err}", file=sys.stderr)
            status = 1
            continue
        if args.sums:
            print(f"{hashes[algorithms[0]]}  {path}")
        else:
            print(path)
            for name, value in hashes.items():
                print(f"  {name:<7}{value}")
    return status


if __name__ == "__main__":
    sys.exit(main())
