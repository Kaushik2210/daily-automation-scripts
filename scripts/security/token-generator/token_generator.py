"""Create random tokens: URL-safe, hex, Base32, numeric PINs or UUIDs."""
import argparse
import base64
import secrets
import sys
import uuid

KINDS = ["urlsafe", "hex", "base32", "numeric", "uuid"]


def make_token(kind="urlsafe", nbytes=32, prefix=""):
    """Return one random token. `nbytes` is the amount of randomness (digits for numeric)."""
    if kind == "urlsafe":
        body = secrets.token_urlsafe(nbytes)
    elif kind == "hex":
        body = secrets.token_hex(nbytes)
    elif kind == "base32":
        body = base64.b32encode(secrets.token_bytes(nbytes)).decode().rstrip("=")
    elif kind == "numeric":
        body = "".join(secrets.choice("0123456789") for _ in range(nbytes))
    elif kind == "uuid":
        body = str(uuid.uuid4())
    else:
        raise ValueError(f"unknown kind: {kind}")
    return prefix + body


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate random tokens.")
    parser.add_argument("--kind", choices=KINDS, default="urlsafe", help="token style")
    parser.add_argument("-b", "--bytes", type=int, default=32,
                        help="bytes of randomness (digits for numeric; ignored for uuid)")
    parser.add_argument("-p", "--prefix", default="", help="text to put in front, e.g. sk_")
    parser.add_argument("-n", "--count", type=int, default=1, help="how many tokens")
    args = parser.parse_args(argv)
    if args.bytes < 1 or args.count < 1:
        parser.error("--bytes and --count must be at least 1")
    if args.kind == "numeric" and args.bytes < 4:
        parser.error("numeric tokens need at least 4 digits")

    for _ in range(args.count):
        print(make_token(args.kind, args.bytes, args.prefix))
    return 0


if __name__ == "__main__":
    sys.exit(main())
