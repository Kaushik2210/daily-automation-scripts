"""Keep notes in one file that is encrypted with a passphrase (scrypt + AES-256-GCM)."""
import argparse
import contextlib
import getpass
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"DAS1"          # file format: MAGIC, log2(N), r, p, salt(16), nonce(12), ciphertext+tag
SCRYPT_LOG2 = 15         # about 32 MB of memory and a fraction of a second per guess
MAX_LOG2 = 20            # refuse files that ask for absurd amounts of memory
HEADER = len(MAGIC) + 3 + 16 + 12
DEFAULT_VAULT = Path.home() / ".note-vault.dat"


def derive_key(passphrase, salt, n_log2, r=8, p=1):
    return Scrypt(salt=salt, length=32, n=2**n_log2, r=r, p=p).derive(passphrase.encode())


def encrypt(data, passphrase):
    salt, nonce = os.urandom(16), os.urandom(12)
    header = MAGIC + bytes([SCRYPT_LOG2, 8, 1]) + salt + nonce
    return header + AESGCM(derive_key(passphrase, salt, SCRYPT_LOG2)).encrypt(nonce, data, header)


def decrypt(blob, passphrase):
    """Return the plaintext, or raise ValueError for a wrong passphrase or a damaged file."""
    if len(blob) < HEADER + 16 or blob[:4] != MAGIC:
        raise ValueError("this isn't an encrypted vault file")
    n_log2, r, p = blob[4], blob[5], blob[6]
    if not 4 <= n_log2 <= MAX_LOG2 or not 1 <= r <= 16 or not 1 <= p <= 4:
        raise ValueError("the file asks for unreasonable key settings; refusing to open it")
    salt, nonce = blob[7:23], blob[23:35]
    try:
        key = derive_key(passphrase, salt, n_log2, r, p)
        return AESGCM(key).decrypt(nonce, blob[HEADER:], blob[:HEADER])
    except InvalidTag:
        raise ValueError("wrong passphrase, or the file has been changed") from None


def get_passphrase(args, creating):
    """From --passphrase-file, then $NOTE_VAULT_PASSPHRASE, then a hidden prompt."""
    if args.passphrase_file:
        text = args.passphrase_file.read_text(encoding="utf-8").splitlines()
        secret = text[0] if text else ""
    elif os.environ.get(args.passphrase_env):
        secret = os.environ[args.passphrase_env]
    else:
        secret = getpass.getpass("Passphrase: ")
        if creating and getpass.getpass("Again: ") != secret:
            raise ValueError("the two passphrases didn't match")
    if not secret:
        raise ValueError("the passphrase can't be empty")
    if creating and len(secret) < 8:
        raise ValueError("use a passphrase of at least 8 characters for a new vault")
    return secret


def save(path, data, passphrase):
    """Write the vault through a temporary file so a crash can't leave half a vault."""
    blob = encrypt(json.dumps(data).encode("utf-8"), passphrase)
    temp = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False,
                                         suffix=".tmp") as handle:
            temp = handle.name
            handle.write(blob)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except OSError:
        if temp:
            Path(temp).unlink(missing_ok=True)
        raise
    with contextlib.suppress(OSError):
        os.chmod(path, 0o600)  # only meaningful on Linux and macOS


def find(notes, title):
    for key in notes:
        if key.lower() == title.lower():
            return key
    return None


def run(args, notes):
    """Apply the command to the notes dict. Returns (changed, text to print)."""
    now = datetime.now().isoformat(timespec="seconds")
    if args.command == "list":
        if not notes:
            return False, "The vault is empty."
        width = max(len(t) for t in notes)
        return False, "\n".join(
            f"{t:<{width}}  updated {n['updated'][:10]}  ({len(n['text'])} chars)"
            for t, n in sorted(notes.items()))
    if args.command == "search":
        if not args.title:
            raise ValueError("search needs some text to look for")
        found = []
        needle = args.title.lower()
        for title, note in sorted(notes.items()):
            text = " ".join(note["text"].split())
            at = text.lower().find(needle)
            if at < 0 and needle not in title.lower():
                continue
            start = max(0, at - 30) if at >= 0 else 0
            end = start + 80
            found.append(f"{title}: {'...' if start else ''}{text[start:end]}"
                         f"{'...' if end < len(text) else ''}")
        return False, "\n".join(found) or "No notes match."
    if not args.title:
        raise ValueError(f"'{args.command}' needs a note title")
    existing = find(notes, args.title)
    if args.command == "show":
        if not existing:
            raise ValueError(f"no note called '{args.title}'")
        return False, notes[existing]["text"]
    if args.command == "delete":
        if not existing:
            raise ValueError(f"no note called '{args.title}'")
        if not args.yes:
            return False, f"Would delete '{existing}'. Add --yes to do it."
        del notes[existing]
        return True, f"Deleted '{existing}'."
    # add
    if args.text is not None:
        text = args.text
    elif args.file:
        text = args.file.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        raise ValueError("give the note with --text or --file, or pipe it in")
    if existing and not args.replace:
        raise ValueError(f"'{existing}' already exists; use --replace to overwrite it")
    created = notes[existing]["created"] if existing else now
    if existing:
        del notes[existing]
    notes[args.title] = {"text": text, "created": created, "updated": now}
    return True, f"{'Replaced' if existing else 'Added'} '{args.title}'."


def main(argv=None):
    parser = argparse.ArgumentParser(description="Notes encrypted with a passphrase.")
    parser.add_argument("command", choices=["add", "list", "show", "search", "delete"])
    parser.add_argument("title", nargs="?", help="note title (or the text to search for)")
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT,
                        help="vault file (~/.note-vault.dat)")
    parser.add_argument("--text", help="the note's text (for add)")
    parser.add_argument("--file", type=Path, help="read the note's text from a file (for add)")
    parser.add_argument("--replace", action="store_true", help="overwrite an existing note (add)")
    parser.add_argument("--yes", action="store_true", help="really delete (delete)")
    parser.add_argument("--passphrase-file", type=Path, dest="passphrase_file",
                        help="file whose first line is the passphrase")
    parser.add_argument("--passphrase-env", default="NOTE_VAULT_PASSPHRASE", metavar="NAME",
                        help="environment variable holding the passphrase (NOTE_VAULT_PASSPHRASE)")
    args = parser.parse_args(argv)

    exists = args.vault.exists()
    if not exists and args.command != "add":
        print(f"No vault at {args.vault}. Create one with the 'add' command.", file=sys.stderr)
        return 1
    try:
        passphrase = get_passphrase(args, creating=not exists)
        notes = json.loads(decrypt(args.vault.read_bytes(), passphrase))["notes"] if exists else {}
        changed, text = run(args, notes)
        if changed:
            save(args.vault, {"notes": notes}, passphrase)
    except (ValueError, OSError, KeyError, UnicodeDecodeError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
