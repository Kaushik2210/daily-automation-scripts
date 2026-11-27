"""Decode a JSON Web Token's header and claims. It reads them; it does not trust them."""
import argparse
import base64
import binascii
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HMAC_ALGORITHMS = {"HS256": hashlib.sha256, "HS384": hashlib.sha384, "HS512": hashlib.sha512}
TIME_CLAIMS = [("iat", "issued at"), ("nbf", "not valid before"), ("exp", "expires")]
KEY_LOOKUP_HEADERS = ("jku", "x5u", "jwk", "kid")


def b64url_decode(text):
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (binascii.Error, ValueError):
        raise ValueError("it isn't valid base64url") from None


def split_token(token):
    token = "".join(token.split())
    if token.lower().startswith("bearer"):
        token = token[6:]
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError(f"a JWT has 3 dot-separated parts, this has {len(parts)}")
    return parts


def decode(token):
    """Return {header, payload, signature (bytes), signing_input}. Nothing is verified."""
    header_b64, payload_b64, signature_b64 = split_token(token)
    parsed = {}
    for name, part in (("header", header_b64), ("payload", payload_b64)):
        try:
            parsed[name] = json.loads(b64url_decode(part))
        except (ValueError, UnicodeDecodeError):
            raise ValueError(f"the {name} isn't valid base64url JSON") from None
        if not isinstance(parsed[name], dict):
            raise ValueError(f"the {name} should be a JSON object")
    parsed["signature"] = b64url_decode(signature_b64) if signature_b64 else b""
    parsed["signing_input"] = f"{header_b64}.{payload_b64}".encode()
    return parsed


def to_time(value):
    try:
        return datetime.fromtimestamp(float(value), UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def timeline(payload, now):
    """[(claim, label, ISO time or the raw value, relative text)] for iat, nbf and exp."""
    rows = []
    for claim, label in TIME_CLAIMS:
        if claim not in payload:
            continue
        moment = to_time(payload[claim])
        if moment is None:
            rows.append((claim, label, str(payload[claim]), "not a valid timestamp"))
            continue
        seconds = int(moment.timestamp() - now)
        size = span_text(abs(seconds))
        rows.append((claim, label, moment.strftime("%Y-%m-%d %H:%M:%S UTC"),
                     f"in {size}" if seconds > 0 else f"{size} ago"))
    return rows


def span_text(span):
    if span >= 86400:
        return f"{span // 86400}d {span % 86400 // 3600}h"
    if span >= 3600:
        return f"{span // 3600}h {span % 3600 // 60}m"
    return f"{span // 60}m {span % 60}s"


def status(payload, now):
    exp, nbf = to_time(payload.get("exp")), to_time(payload.get("nbf"))
    if exp and exp.timestamp() <= now:
        return "EXPIRED"
    if nbf and nbf.timestamp() > now:
        return "NOT YET VALID"
    return "within its validity window" if exp else "no expiry claim"


def warnings(header, payload, now):
    found = []
    alg = str(header.get("alg", ""))
    if alg.lower() == "none":
        found.append("alg is 'none': the token is unsigned, so anyone could have written it")
    elif alg in HMAC_ALGORITHMS:
        found.append(f"{alg} uses a shared secret, so it can only be checked by someone who has it")
    if not alg:
        found.append("the header has no alg")
    for name in KEY_LOOKUP_HEADERS:
        if name in header:
            found.append(f"the header names its own key ({name}); a server must not trust that")
    if "exp" not in payload:
        found.append("no exp claim: this token never expires")
    else:
        exp = to_time(payload["exp"])
        if exp and exp.timestamp() - now > 366 * 86400:
            found.append("expires more than a year from now, which is a long time for a token")
    if "aud" not in payload and "iss" not in payload:
        found.append("no iss or aud claim to say who issued it or who it is for")
    return found


def check_signature(parsed, header, secret):
    """HMAC check for HS256/384/512. Returns True, False, or None when it can't be checked."""
    algorithm = HMAC_ALGORITHMS.get(str(header.get("alg")))
    if algorithm is None:
        return None
    expected = hmac.new(secret.encode(), parsed["signing_input"], algorithm).digest()
    return hmac.compare_digest(expected, parsed["signature"])


def moment_to_seconds(text):
    """A unix time or an ISO date-time (taken as UTC when it has no zone) -> seconds."""
    try:
        return float(text)
    except ValueError:
        moment = datetime.fromisoformat(text)
        return (moment if moment.tzinfo else moment.replace(tzinfo=UTC)).timestamp()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Decode a JWT without trusting it.")
    parser.add_argument("token", nargs="?", help="the token (or use --file, or pipe it in)")
    parser.add_argument("--file", type=Path, help="read the token from a file")
    parser.add_argument("--now", help="treat this unix time or ISO date-time as now")
    parser.add_argument("--secret-env", metavar="NAME",
                        help="environment variable holding an HMAC secret, to check HS256/384/512")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    try:
        if args.token:
            token = args.token
        elif args.file:
            token = args.file.read_text(encoding="utf-8")
        elif not sys.stdin.isatty():
            token = sys.stdin.read()
        else:
            parser.error("give a token, --file, or pipe one in")
        now = moment_to_seconds(args.now) if args.now else time.time()
        parsed = decode(token)
    except (ValueError, OSError) as err:
        print(f"Can't decode that token: {err}", file=sys.stderr)
        return 1
    header, payload = parsed["header"], parsed["payload"]
    verdict = None
    if args.secret_env:
        secret = os.environ.get(args.secret_env)
        if not secret:
            print(f"Error: ${args.secret_env} is not set", file=sys.stderr)
            return 1
        verdict = check_signature(parsed, header, secret)

    notes = warnings(header, payload, now)
    state = status(payload, now)
    if args.format == "json":
        print(json.dumps({"verified": verdict, "header": header, "payload": payload,
                          "status": state, "warnings": notes,
                          "signature_bytes": len(parsed["signature"])}, indent=1))
    else:
        print("NOT VERIFIED: this only reads the token; anyone can forge one that decodes alike.")
        if verdict is True:
            print("Signature: valid for the secret you provided")
        elif verdict is False:
            print("Signature: INVALID for the secret you provided")
        elif args.secret_env:
            print(f"Signature: can't be checked here (algorithm {header.get('alg')})")
        print("\nHeader:\n" + json.dumps(header, indent=2))
        print("\nClaims:\n" + json.dumps(payload, indent=2))
        rows = timeline(payload, now)
        if rows:
            print("\nTimes:")
            for claim, label, when, relative in rows:
                print(f"  {claim:<4} {label:<17} {when}  ({relative})")
        print(f"\nStatus: {state}")
        print(f"Signature part: {len(parsed['signature'])} byte(s)")
        if notes:
            print("\nWorth knowing:")
            print("\n".join(f"  - {n}" for n in notes))
    return 1 if verdict is False else 0


if __name__ == "__main__":
    sys.exit(main())
