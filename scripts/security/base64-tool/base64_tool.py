"""Encode or decode text and files as Base64 (standard or URL-safe)."""
import argparse
import base64
import binascii
import sys
from pathlib import Path


def encode(data, url_safe=False):
    encoder = base64.urlsafe_b64encode if url_safe else base64.b64encode
    return encoder(data).decode("ascii")


def decode(text, url_safe=False):
    """Decode Base64 text; missing '=' padding and whitespace are tolerated."""
    cleaned = "".join(text.split())
    cleaned += "=" * (-len(cleaned) % 4)
    decoder = base64.urlsafe_b64decode if url_safe else base64.b64decode
    return decoder(cleaned)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Base64 encode or decode text and files.")
    parser.add_argument("text", nargs="?", help="text to convert (or use --file / stdin)")
    parser.add_argument("-f", "--file", type=Path, help="read the input from this file")
    parser.add_argument("-d", "--decode", action="store_true", help="decode instead of encode")
    parser.add_argument("--url-safe", action="store_true", help="use the URL-safe alphabet")
    parser.add_argument("-o", "--output", type=Path, help="write the result to this file")
    parser.add_argument("--apply", action="store_true",
                        help="really write --output (default only prints text results)")
    args = parser.parse_args(argv)

    if args.file:
        raw = args.file.read_bytes()
    elif args.text is not None:
        raw = args.text.encode("utf-8")
    else:
        raw = sys.stdin.buffer.read()

    try:
        result = decode(raw.decode("ascii", "ignore"), args.url_safe) if args.decode \
            else encode(raw, args.url_safe).encode("ascii")
    except (binascii.Error, ValueError) as err:
        print(f"Not valid Base64: {err}", file=sys.stderr)
        return 1

    if args.output and args.apply:
        args.output.write_bytes(result)
        print(f"Wrote {len(result)} byte(s) to {args.output}.")
        return 0
    try:
        print(result.decode("utf-8"))
    except UnicodeDecodeError:
        print(f"The result is {len(result)} bytes of binary data; use -o FILE --apply to save it.",
              file=sys.stderr)
        return 1
    if args.output:
        print(f"(preview only: use --apply to write {args.output})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
