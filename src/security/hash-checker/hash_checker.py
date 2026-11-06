"""Check that a file matches an expected checksum (MD5, SHA-1, SHA-256 or SHA-512)."""
import argparse
import hashlib
import hmac
import re
import sys
from pathlib import Path

BY_LENGTH = {32: "md5", 40: "sha1", 64: "sha256", 128: "sha512"}


def file_digest(path, algorithm, chunk=1024 * 1024):
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def clean_expected(text):
    """Accept '<hash>', '<hash>  file.iso' (sha256sum style) or 'SHA256:<hash>'."""
    token = text.strip().split()[0] if text.strip() else ""
    token = re.sub(r"^[A-Za-z0-9-]+[:=]", "", token)
    return token.lower()


def guess_algorithm(expected):
    return BY_LENGTH.get(len(expected))


def matches(actual, expected):
    return hmac.compare_digest(actual.lower(), expected.lower())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify a file against an expected checksum.")
    parser.add_argument("file", type=Path)
    parser.add_argument("expected", help="expected hash, or a path to a checksum file")
    parser.add_argument("-a", "--algorithm", choices=sorted(set(BY_LENGTH.values())),
                        help="hash algorithm (default: guessed from the hash length)")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")

    source = args.expected
    if Path(source).is_file():
        source = Path(source).read_text(encoding="utf-8").splitlines()[0]
    expected = clean_expected(source)
    algorithm = args.algorithm or guess_algorithm(expected)
    if not algorithm or not re.fullmatch(r"[0-9a-f]+", expected):
        parser.error("couldn't tell the algorithm; check the hash or pass --algorithm")

    actual = file_digest(args.file, algorithm)
    if matches(actual, expected):
        print(f"OK: {args.file.name} matches the expected {algorithm} hash.")
        return 0
    print(f"MISMATCH: {args.file.name}\n  expected {expected}\n  actual   {actual}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
