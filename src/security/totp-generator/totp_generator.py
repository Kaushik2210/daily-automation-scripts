"""Generate and verify time-based one-time passwords (TOTP, RFC 6238) from a base32 secret."""
import argparse
import base64
import binascii
import hashlib
import hmac
import json
import os
import struct
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ALGORITHMS = {"SHA1": hashlib.sha1, "SHA256": hashlib.sha256, "SHA512": hashlib.sha512}


def clean_secret(text):
    """Accept spaces, dashes and lowercase; return the secret as bytes."""
    compact = "".join(text.split()).replace("-", "").upper().rstrip("=")
    if not compact:
        raise ValueError("the secret is empty")
    try:
        return base64.b32decode(compact + "=" * (-len(compact) % 8))
    except (binascii.Error, ValueError):
        raise ValueError("the secret isn't valid base32 (A-Z and 2-7 only)") from None


def hotp(key, counter, digits=6, algorithm="SHA1"):
    """RFC 4226 HOTP value for a counter, as a zero-padded string."""
    digest = hmac.new(key, struct.pack(">Q", counter), ALGORITHMS[algorithm]).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**digits).zfill(digits)


def totp(key, moment, period=30, digits=6, algorithm="SHA1"):
    return hotp(key, int(moment // period), digits, algorithm)


def parse_uri(uri):
    """An otpauth://totp/Label?secret=...&issuer=... URI -> settings dict."""
    parts = urlparse(uri)
    if parts.scheme != "otpauth" or parts.netloc != "totp":
        raise ValueError("expected an otpauth://totp/... address")
    query = {k: v[0] for k, v in parse_qs(parts.query).items()}
    if "secret" not in query:
        raise ValueError("the address has no secret=")
    algorithm = query.get("algorithm", "SHA1").upper()
    if algorithm not in ALGORITHMS:
        raise ValueError(f"unsupported algorithm {algorithm}")
    return {"secret": query["secret"], "digits": int(query.get("digits", 6)),
            "period": int(query.get("period", 30)), "algorithm": algorithm,
            "label": unquote(parts.path.lstrip("/")), "issuer": query.get("issuer", "")}


def read_secret(args):
    """From --uri, --secret-file, --secret or the environment, in that order."""
    if args.uri:
        return parse_uri(args.uri)
    if args.secret_file:
        lines = args.secret_file.read_text(encoding="utf-8").splitlines()
        return {"secret": lines[0] if lines else ""}
    if args.secret:
        print("Note: a secret on the command line stays in your shell history; prefer "
              "--secret-file or $TOTP_SECRET.", file=sys.stderr)
        return {"secret": args.secret}
    if os.environ.get(args.secret_env):
        return {"secret": os.environ[args.secret_env]}
    raise ValueError("give the secret with --secret-file, $TOTP_SECRET, --uri or --secret")


def when(text):
    """A unix time or an ISO date/time -> seconds."""
    try:
        return float(text)
    except ValueError:
        return datetime.fromisoformat(text).timestamp()


def verify(key, code, moment, window, period, digits, algorithm):
    """True if `code` matches the current step or one of `window` steps either side."""
    code = "".join(code.split())
    for step in range(-window, window + 1):
        expected = totp(key, moment + step * period, period, digits, algorithm)
        if hmac.compare_digest(expected.encode(), code.encode()):
            return True
    return False


def group(code):
    half = len(code) // 2
    return f"{code[:half]} {code[half:]}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate TOTP codes from a base32 secret.")
    parser.add_argument("--secret-file", type=Path, dest="secret_file",
                        help="file whose first line is the base32 secret")
    parser.add_argument("--secret-env", default="TOTP_SECRET", metavar="NAME",
                        help="environment variable holding the secret (TOTP_SECRET)")
    parser.add_argument("--secret", help="the base32 secret (visible in shell history)")
    parser.add_argument("--uri", help="an otpauth://totp/... address (e.g. from a QR code)")
    parser.add_argument("--digits", type=int, choices=[6, 7, 8], help="code length (6)")
    parser.add_argument("--period", type=int, help="seconds per code (30)")
    parser.add_argument("--algorithm", choices=sorted(ALGORITHMS), help="hash (SHA1)")
    parser.add_argument("--time", help="use this unix time or ISO date-time instead of now")
    parser.add_argument("--count", type=int, default=1,
                        help="how many codes to show, now and next (1)")
    parser.add_argument("--verify", metavar="CODE", help="check a code; exit 0 if it is valid")
    parser.add_argument("--window", type=int, default=1,
                        help="steps either side that --verify accepts (1)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    if not 1 <= args.count <= 20 or args.window < 0:
        parser.error("--count must be 1-20 and --window not negative")
    try:
        settings = read_secret(args)
        key = clean_secret(settings["secret"])
        digits = args.digits or settings.get("digits", 6)
        period = args.period or settings.get("period", 30)
        algorithm = args.algorithm or settings.get("algorithm", "SHA1")
        moment = when(args.time) if args.time else time.time()
    except (ValueError, OSError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    if args.verify is not None:
        ok = verify(key, args.verify, moment, args.window, period, digits, algorithm)
        print("valid" if ok else "invalid")
        return 0 if ok else 1
    remaining = period - int(moment % period)
    codes = [totp(key, moment + i * period, period, digits, algorithm) for i in range(args.count)]
    if args.format == "json":
        print(json.dumps({"code": codes[0], "valid_for_seconds": remaining, "period": period,
                          "digits": digits, "algorithm": algorithm, "next": codes[1:]}))
        return 0
    print(f"{group(codes[0])}   (valid for {remaining} more second(s))")
    for number, code in enumerate(codes[1:], 1):
        print(f"{group(code)}   (in {remaining + (number - 1) * period} s)")
    if len(key) < 10:
        print("Warning: this secret is shorter than 80 bits; real services use longer ones.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
