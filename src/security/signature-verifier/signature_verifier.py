"""Verify a GnuPG signature and say, in plain words, what it does and doesn't prove."""
import argparse
import json
import shutil
import subprocess  # web-ok: gpg only runs without --from-status; saved gpg output works anywhere
import sys
from datetime import UTC, datetime
from pathlib import Path

PREFIX = "[GNUPG:] "
TRUST_RANK = {"never": -1, "undefined": 0, "marginal": 1, "fully": 2, "ultimate": 3}
TRUST_ALIAS = {"full": "fully"}  # the command line says full, gpg says TRUST_FULLY
WORDS = {"good": "GOOD", "expired_key": "GOOD, BUT THE KEY HAS EXPIRED",
         "expired_signature": "THE SIGNATURE HAS EXPIRED", "revoked_key": "KEY REVOKED",
         "bad": "BAD: the file or the signature has been changed",
         "unknown_key": "CAN'T CHECK: the signer's public key isn't in your keyring",
         "none": "NO SIGNATURE FOUND"}


SEVERITY = {"none": 0, "good": 1, "unknown_key": 2, "expired_key": 3, "expired_signature": 4,
            "revoked_key": 5, "bad": 6}
VERDICTS = {"GOODSIG": "good", "EXPSIG": "expired_signature", "EXPKEYSIG": "expired_key",
            "REVKEYSIG": "revoked_key", "BADSIG": "bad", "ERRSIG": "unknown_key",
            "NO_PUBKEY": "unknown_key"}


def parse_status(text):
    """Turn `gpg --status-fd` output into a result dict. Only [GNUPG:] lines are read.

    If a file carries several signatures, the worst outcome is reported, so a bad signature
    can never be hidden behind a good one.
    """
    result = {"verdict": "none", "signer": None, "key_id": None, "fingerprint": None,
              "primary_fingerprint": None, "signed_on": None, "trust": None}
    reporting = False  # do the detail lines that follow belong to the signature we report?
    for raw in text.splitlines():
        if not raw.startswith(PREFIX):
            continue
        parts = raw[len(PREFIX):].split(" ")
        word, rest = parts[0], parts[1:]
        if word in VERDICTS:
            verdict = VERDICTS[word]
            reporting = SEVERITY[verdict] > SEVERITY[result["verdict"]]
            if reporting:
                result.update(verdict=verdict, key_id=rest[0] if rest else None,
                              signer=(" ".join(rest[1:]) or None) if word != "ERRSIG" else None,
                              fingerprint=None, primary_fingerprint=None, signed_on=None,
                              trust=None)
        elif word == "VALIDSIG" and reporting and len(rest) >= 3:
            result["fingerprint"] = rest[0]
            result["primary_fingerprint"] = rest[-1] if len(rest[-1]) >= 32 else rest[0]
            if rest[2].isdigit():
                result["signed_on"] = datetime.fromtimestamp(int(rest[2]), UTC).strftime("%Y-%m-%d")
        elif word.startswith("TRUST_") and reporting:
            result["trust"] = word[6:].lower()
    return result


def normalise(fingerprint):
    return "".join(fingerprint.split()).upper()


def judge(result, expected, require_trust):
    """Return (ok, reasons). A signature is only accepted if every requirement is met."""
    reasons = []
    if result["verdict"] != "good":
        reasons.append(WORDS[result["verdict"]])
    if expected:
        wanted = {normalise(f) for f in expected}
        seen = {normalise(f) for f in (result["fingerprint"], result["primary_fingerprint"]) if f}
        if not wanted & seen:
            reasons.append("the signing key is not one of the fingerprints you expected")
    if require_trust:
        have = TRUST_RANK.get(result["trust"] or "undefined", 0)
        if have < TRUST_RANK[TRUST_ALIAS.get(require_trust, require_trust)]:
            reasons.append(f"the key's trust is '{result['trust'] or 'undefined'}', "
                           f"below the required '{require_trust}'")
    return not reasons, reasons


def space(fingerprint):
    return " ".join(fingerprint[i:i + 4] for i in range(0, len(fingerprint), 4))


def run_gpg(gpg, signature, target, homedir, timeout=60):
    command = [gpg, "--status-fd", "1", "--batch", "--no-tty"]
    if homedir:
        command += ["--homedir", str(homedir)]
    command += ["--verify", str(signature)] + ([str(target)] if target else [])
    done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, check=False)
    return done.stdout, done.stderr


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify a GnuPG signature.")
    parser.add_argument("signature", nargs="?", type=Path,
                        help="the signature file (.sig or .asc), or a clear-signed file")
    parser.add_argument("target", nargs="?", type=Path,
                        help="the signed file, for a detached signature")
    parser.add_argument("--from-status", type=Path, dest="status",
                        help="saved `gpg --status-fd 1 --verify` output instead of running gpg")
    parser.add_argument("--expect-fingerprint", action="append", default=[], metavar="FPR",
                        help="only accept a signature made by this key (repeatable)")
    parser.add_argument("--require-trust", choices=["marginal", "full", "ultimate"],
                        help="also require this level of trust in the key")
    parser.add_argument("--homedir", help="use this GnuPG home folder (passed to gpg as given)")
    parser.add_argument("--gpg", default="gpg", help="the gpg program (gpg)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    try:
        if args.status:
            status_text = args.status.read_text(encoding="utf-8")
        else:
            if not args.signature:
                parser.error("give a signature file (and the signed file), or --from-status")
            if not shutil.which(args.gpg):
                print(f"Can't find '{args.gpg}'. Install GnuPG, or use --from-status.",
                      file=sys.stderr)
                return 1
            for path in (args.signature, args.target):
                if path and not path.is_file():
                    print(f"Not a file: {path}", file=sys.stderr)
                    return 1
            status_text, _ = run_gpg(args.gpg, args.signature, args.target, args.homedir)
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as err:
        print(f"Can't verify: {err}", file=sys.stderr)
        return 1

    result = parse_status(status_text)
    ok, reasons = judge(result, args.expect_fingerprint, args.require_trust)
    if args.format == "json":
        print(json.dumps({**result, "accepted": ok, "problems": reasons}, indent=1))
        return 0 if ok else 1
    print(f"Signature: {WORDS[result['verdict']]}")
    if result["signer"] or result["key_id"]:
        print(f"  Signer:      {result['signer'] or '(unknown)'} (key {result['key_id']})")
    if result["fingerprint"]:
        print(f"  Fingerprint: {space(result['primary_fingerprint'] or result['fingerprint'])}")
    if result["signed_on"]:
        print(f"  Signed on:   {result['signed_on']}")
    if result["trust"]:
        print(f"  Key trust:   {result['trust']}")
    if result["verdict"] in ("good", "expired_key") and result["trust"] in (None, "undefined"):
        print("\nNote: the key isn't certified by you or anyone you trust. A good signature "
              "proves the file matches that key, not who owns the key; check the fingerprint "
              "with the signer another way.")
    for reason in reasons:
        if reason != WORDS[result["verdict"]]:
            print(f"Rejected: {reason}")
    print("\nAccepted." if ok else "\nNot accepted.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
