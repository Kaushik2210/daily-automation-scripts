"""Review SSH keys for weak types, short lengths, age, missing passphrases and open permissions."""
import argparse
import base64
import hashlib
import os
import stat
import struct
import sys
import time
from pathlib import Path

KEY_TYPES = ("ssh-ed25519", "ssh-rsa", "ssh-dss", "ecdsa-sha2-nistp256", "ecdsa-sha2-nistp384",
             "ecdsa-sha2-nistp521", "sk-ssh-ed25519@openssh.com",
             "sk-ecdsa-sha2-nistp256@openssh.com")
CURVE_BITS = {"nistp256": 256, "nistp384": 384, "nistp521": 521}
PRIVATE_MARKERS = ("-----BEGIN OPENSSH PRIVATE KEY-----", "-----BEGIN RSA PRIVATE KEY-----",
                   "-----BEGIN DSA PRIVATE KEY-----", "-----BEGIN EC PRIVATE KEY-----",
                   "-----BEGIN PRIVATE KEY-----", "-----BEGIN ENCRYPTED PRIVATE KEY-----")


def read_string(data, offset):
    (length,) = struct.unpack_from(">I", data, offset)
    return data[offset + 4:offset + 4 + length], offset + 4 + length


def parse_public_key(line):
    """Return a dict (type, bits, fingerprint, comment, options) or None if it isn't a key line."""
    parts = line.strip().split()
    for index, word in enumerate(parts):
        if word in KEY_TYPES and index + 1 < len(parts):
            try:
                blob = base64.b64decode(parts[index + 1], validate=True)
                key_type, offset = read_string(blob, 0)
                bits = None
                if key_type == b"ssh-rsa":
                    _exponent, offset = read_string(blob, offset)
                    modulus, _ = read_string(blob, offset)
                    bits = int.from_bytes(modulus, "big").bit_length()
                elif key_type == b"ssh-dss":
                    prime, _ = read_string(blob, offset)
                    bits = int.from_bytes(prime, "big").bit_length()
                elif key_type.startswith(b"ecdsa-sha2-") or key_type.startswith(b"sk-ecdsa"):
                    bits = CURVE_BITS.get(word.split("-")[-1].split("@")[0], 256)
                else:
                    bits = 256
            except (ValueError, struct.error):
                return None
            digest = base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
            return {"type": word, "bits": bits, "fingerprint": f"SHA256:{digest}",
                    "comment": " ".join(parts[index + 2:]),
                    "options": " ".join(parts[:index])}
    return None


def judge_key(key):
    """Return (verdict, advice): verdict is OK, NOTE or WEAK."""
    kind, bits = key["type"], key["bits"]
    if kind == "ssh-dss":
        return "WEAK", "DSA keys are obsolete and disabled in modern OpenSSH; replace with ed25519"
    if kind == "ssh-rsa":
        if bits < 2048:
            return "WEAK", f"RSA {bits}-bit is too short; use ed25519 or RSA 3072+"
        if bits < 3072:
            return "NOTE", f"RSA {bits}-bit is acceptable but ed25519 is stronger and shorter"
        return "OK", f"RSA {bits}-bit"
    if kind.startswith("sk-"):
        return "OK", "hardware-backed key"
    if kind.startswith("ecdsa"):
        return "OK", f"ECDSA {bits}-bit"
    return "OK", "ed25519"


def private_key_state(text):
    """For a private key file's text return 'encrypted', 'unencrypted' or None (not a key)."""
    lines = text.splitlines()
    marker = lines[0].strip() if lines else ""
    if marker not in PRIVATE_MARKERS:
        return None
    if marker == "-----BEGIN ENCRYPTED PRIVATE KEY-----" or "ENCRYPTED" in "".join(lines[1:3]):
        return "encrypted"
    if marker == "-----BEGIN OPENSSH PRIVATE KEY-----":
        try:
            body = "".join(row for row in lines[1:] if not row.startswith(("(", "-----")))
            raw = base64.b64decode(body[:96] + "=" * (-len(body[:96]) % 4))
            if not raw.startswith(b"openssh-key-v1\x00"):
                return None
            cipher, _ = read_string(raw, 15)
            return "unencrypted" if cipher == b"none" else "encrypted"
        except (ValueError, struct.error):
            return None
    return "unencrypted"


def looks_like_key_file(path):
    return path.suffix == ".pub" or path.name.startswith("authorized_keys")


def audit_path(path, max_age_days=None, now=None, explicit=True):
    """Return a list of findings (verdict, text) for one file.

    Files found by scanning a folder (explicit=False) are only reported if they hold keys,
    so other files lying around next to your keys don't produce noise.
    """
    findings = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as err:
        return [("NOTE", f"couldn't read ({err.strerror or err})")]
    now = now or time.time()
    age = int((now - path.stat().st_mtime) / 86400)
    state = private_key_state(text)
    if state:
        findings.append(("WEAK" if state == "unencrypted" else "OK",
                         "private key has NO passphrase - anyone who copies it can use it"
                         if state == "unencrypted" else "private key is passphrase-protected"))
        if os.name == "posix" and stat.S_IMODE(path.stat().st_mode) & 0o077:
            mode = format(stat.S_IMODE(path.stat().st_mode), "04o")
            findings.append(("WEAK", f"permissions {mode} let other users read it; run chmod 600"))
    else:
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key = parse_public_key(line)
            if key is None:
                if explicit or looks_like_key_file(path):
                    findings.append(("NOTE", "a line that isn't a valid public key was skipped"))
                continue
            verdict, advice = judge_key(key)
            extra = f", restricted by options: {key['options']}" if key["options"] else ""
            label = key["comment"] or "(no comment)"
            findings.append((verdict, f"{key['type']} {advice} - {label} {key['fingerprint']}"
                                      f"{extra}"))
    if max_age_days is not None and age > max_age_days and findings:
        findings.append(("NOTE", f"file last changed {age} days ago (limit {max_age_days})"))
    return findings


def candidate_files(paths):
    found = []
    for path in paths:
        if path.is_dir():
            found += sorted(p for p in path.iterdir() if p.is_file() and p.stat().st_size < 100_000
                            and p.name not in ("known_hosts", "config"))
        elif path.is_file():
            found.append(path)
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit SSH keys.")
    parser.add_argument("paths", nargs="*", type=Path,
                        help="key files or folders (default: ~/.ssh)")
    parser.add_argument("--max-age-days", type=int, help="note files older than this many days")
    args = parser.parse_args(argv)
    paths = args.paths or [Path.home() / ".ssh"]
    for path in paths:
        if not path.exists():
            parser.error(f"not found: {path}")

    weak = notes = keys = 0
    explicit = {p for p in paths if p.is_file()}
    for path in candidate_files(paths):
        findings = audit_path(path, args.max_age_days, explicit=path in explicit)
        if not findings:
            continue
        print(path.name)
        for verdict, text in findings:
            keys += 1
            weak += verdict == "WEAK"
            notes += verdict == "NOTE"
            print(f"  [{verdict:<4}] {text}")
    if not keys:
        print("No SSH keys found.")
        return 1
    print(f"\n{keys} item(s) reviewed: {weak} weak, {notes} note(s). Nothing was changed.")
    return 1 if weak else 0


if __name__ == "__main__":
    sys.exit(main())
