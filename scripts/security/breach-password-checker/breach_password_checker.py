"""Check whether a password appears in known breaches, using Have I Been Pwned's k-anonymity API.

Only the first 5 characters of the password's SHA-1 hash ever leave your computer; the password
itself and the rest of the hash are compared locally against the list HIBP sends back.
"""
import argparse
import getpass
import hashlib
import re
import sys
import urllib.error  # web-ok: the network is only used for live checks
import urllib.request
from pathlib import Path

API = "https://api.pwnedpasswords.com/range/"
HEX_SHA1 = re.compile(r"^[0-9A-Fa-f]{40}$")


def sha1_of(password):
    return hashlib.sha1(password.encode("utf-8")).hexdigest().upper()  # HIBP indexes SHA-1 hashes


def split_hash(digest):
    return digest[:5], digest[5:]


def fetch_range(prefix, timeout=10):
    """Download the list of hash suffixes that share this prefix (padded, so sizes don't leak)."""
    request = urllib.request.Request(API + prefix, headers={
        "Add-Padding": "true", "User-Agent": "daily-automation-scripts/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(5 * 1024 * 1024).decode("utf-8", errors="replace")


def count_in_range(range_text, suffix):
    """How many times `suffix` appears in a range response (0 if it doesn't, or is padding)."""
    for line in range_text.splitlines():
        found, _, number = line.strip().partition(":")
        if found.upper() == suffix.upper() and number.isdigit():
            return int(number)
    return 0


def describe(count):
    if count == 0:
        return "Not found in any known breach. (That doesn't prove it's strong - see below.)"
    plural = "time" if count == 1 else "times"
    return f"FOUND: this password has appeared {count:,} {plural} in data breaches. Don't use it."


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check a password against Have I Been Pwned without revealing it.")
    parser.add_argument("--stdin", action="store_true",
                        help="read the password from standard input instead of asking for it")
    parser.add_argument("--sha1", metavar="HASH",
                        help="check a SHA-1 hash (40 hex characters) instead of a password")
    parser.add_argument("--range-file", type=Path,
                        help="read a saved range response instead of asking the API")
    parser.add_argument("--timeout", type=float, default=10, help="seconds to wait (10)")
    args = parser.parse_args(argv)

    if args.sha1:
        if not HEX_SHA1.match(args.sha1):
            parser.error("--sha1 must be 40 hexadecimal characters")
        digest = args.sha1.upper()
    else:
        if args.stdin:
            password = sys.stdin.readline().rstrip("\r\n")
        else:
            password = getpass.getpass("Password to check (it won't be shown): ")
        if not password:
            print("No password given.", file=sys.stderr)
            return 1
        digest = sha1_of(password)
    prefix, suffix = split_hash(digest)

    try:
        text = (args.range_file.read_text(encoding="utf-8") if args.range_file
                else fetch_range(prefix, args.timeout))
    except (urllib.error.URLError, OSError) as err:
        print(f"Couldn't get the range for {prefix}: {getattr(err, 'reason', err)}",
              file=sys.stderr)
        return 1
    count = count_in_range(text, suffix)
    candidates = len(text.splitlines())
    print(f"Checked hash prefix {prefix}.... ({candidates:,} candidate hashes returned)")
    print(describe(count))
    if not count:
        print("A password not in breaches can still be weak: use a long passphrase and a "
              "password manager.")
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main())
