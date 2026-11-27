"""A small encrypted password store for the terminal (scrypt + AES-256-GCM)."""
import argparse
import contextlib
import getpass
import json
import os
import secrets
import string
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"DAS1"          # file format: MAGIC, log2(N), r, p, salt(16), nonce(12), ciphertext+tag
SCRYPT_LOG2 = 15
MAX_LOG2 = 20
HEADER = len(MAGIC) + 3 + 16 + 12
DEFAULT_VAULT = Path.home() / ".password-vault.dat"
SYMBOLS = "!@#$%^&*-_=+?"


def derive_key(passphrase, salt, n_log2, r=8, p=1):
    return Scrypt(salt=salt, length=32, n=2**n_log2, r=r, p=p).derive(passphrase.encode())


def encrypt(data, passphrase):
    salt, nonce = os.urandom(16), os.urandom(12)
    header = MAGIC + bytes([SCRYPT_LOG2, 8, 1]) + salt + nonce
    return header + AESGCM(derive_key(passphrase, salt, SCRYPT_LOG2)).encrypt(nonce, data, header)


def decrypt(blob, passphrase):
    if len(blob) < HEADER + 16 or blob[:4] != MAGIC:
        raise ValueError("this isn't an encrypted vault file")
    n_log2, r, p = blob[4], blob[5], blob[6]
    if not 4 <= n_log2 <= MAX_LOG2 or not 1 <= r <= 16 or not 1 <= p <= 4:
        raise ValueError("the file asks for unreasonable key settings; refusing to open it")
    try:
        key = derive_key(passphrase, blob[7:23], n_log2, r, p)
        return AESGCM(key).decrypt(blob[23:35], blob[HEADER:], blob[:HEADER])
    except InvalidTag:
        raise ValueError("wrong passphrase, or the file has been changed") from None


def read_secret(file, env, prompt, confirm=False):
    """A secret from a file's first line, an environment variable, or a hidden prompt."""
    if file:
        lines = file.read_text(encoding="utf-8").splitlines()
        value = lines[0] if lines else ""
    elif env and os.environ.get(env):
        value = os.environ[env]
    else:
        value = getpass.getpass(prompt)
        if confirm and getpass.getpass("Again: ") != value:
            raise ValueError("the two entries didn't match")
    if not value:
        raise ValueError("that can't be empty")
    return value


def generate(length=20, symbols=True):
    """A random password with at least one lowercase, uppercase, digit (and symbol) character."""
    if length < 8:
        raise ValueError("use a length of at least 8")
    groups = [string.ascii_lowercase, string.ascii_uppercase, string.digits]
    if symbols:
        groups.append(SYMBOLS)
    pool = "".join(groups)
    while True:
        text = "".join(secrets.choice(pool) for _ in range(length))
        if all(any(c in group for c in text) for group in groups):
            return text


def save(path, data, passphrase):
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
        os.chmod(path, 0o600)


def find(entries, name):
    return next((key for key in entries if key.lower() == name.lower()), None)


def run(args, entries):
    """Apply the command. Returns (changed, text)."""
    if args.command == "list":
        if not entries:
            return False, "The vault is empty."
        width = max(len(n) for n in entries)
        lines = []
        for name, entry in sorted(entries.items()):
            age = (date.today() - date.fromisoformat(entry["updated"][:10])).days
            stale = f"  [not changed for {age} days]" if age > args.stale_days else ""
            lines.append(f"{name:<{width}}  {entry['username'] or '-':<24} "
                         f"updated {entry['updated'][:10]}{stale}")
        return False, "\n".join(lines)
    if not args.name:
        raise ValueError(f"'{args.command}' needs an entry name")
    existing = find(entries, args.name)
    if args.command == "get":
        if not existing:
            raise ValueError(f"no entry called '{args.name}'")
        entry = entries[existing]
        if args.password_only:
            return False, entry["password"]
        lines = [f"Name:      {existing}", f"Username:  {entry['username'] or '-'}"]
        if entry["url"]:
            lines.append(f"URL:       {entry['url']}")
        if entry["notes"]:
            lines.append(f"Notes:     {entry['notes']}")
        lines.append(f"Password:  {entry['password'] if args.show else '********  (add --show)'}")
        lines.append(f"Updated:   {entry['updated'][:10]}")
        return False, "\n".join(lines)
    if args.command == "delete":
        if not existing:
            raise ValueError(f"no entry called '{args.name}'")
        if not args.yes:
            return False, f"Would delete '{existing}'. Add --yes to do it."
        del entries[existing]
        return True, f"Deleted '{existing}'."
    # add
    if existing and not args.replace:
        raise ValueError(f"'{existing}' already exists; use --replace to overwrite it")
    if args.generate:
        password = generate(args.generate, not args.no_symbols)
    else:
        password = read_secret(args.password_file, args.password_env, "Password for the entry: ",
                               confirm=True)
    if existing:
        del entries[existing]
    entries[args.name] = {"username": args.username or "", "password": password,
                          "url": args.url or "", "notes": args.notes or "",
                          "updated": datetime.now().isoformat(timespec="seconds")}
    shown = f" Generated password: {password}" if args.generate else ""
    return True, f"{'Replaced' if existing else 'Added'} '{args.name}'.{shown}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Minimal encrypted password store.")
    parser.add_argument("command", choices=["add", "get", "list", "delete", "generate"])
    parser.add_argument("name", nargs="?", help="entry name")
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT,
                        help="vault file (~/.password-vault.dat)")
    parser.add_argument("--username")
    parser.add_argument("--url")
    parser.add_argument("--notes")
    parser.add_argument("--generate", type=int, metavar="LENGTH",
                        help="for add: make a random password of this length")
    parser.add_argument("--no-symbols", action="store_true", help="generated passwords: no symbols")
    parser.add_argument("--length", type=int, default=20, help="for generate: length (20)")
    parser.add_argument("--password-file", type=Path, dest="password_file",
                        help="for add: file whose first line is the entry's password")
    parser.add_argument("--password-env", default="VAULT_ENTRY_PASSWORD", metavar="NAME",
                        help="for add: environment variable holding the entry's password")
    parser.add_argument("--replace", action="store_true", help="overwrite an existing entry (add)")
    parser.add_argument("--show", action="store_true", help="for get: reveal the password")
    parser.add_argument("--password-only", action="store_true",
                        help="for get: print only the password, for piping")
    parser.add_argument("--yes", action="store_true", help="really delete (delete)")
    parser.add_argument("--stale-days", type=int, default=365,
                        help="for list: flag entries unchanged this long (365)")
    parser.add_argument("--passphrase-file", type=Path, dest="passphrase_file",
                        help="file whose first line is the vault passphrase")
    parser.add_argument("--passphrase-env", default="PASSWORD_VAULT_PASSPHRASE", metavar="NAME",
                        help="environment variable holding the vault passphrase")
    args = parser.parse_args(argv)

    if args.command == "generate":
        try:
            print(generate(args.length, not args.no_symbols))
        except ValueError as err:
            parser.error(str(err))
        return 0
    exists = args.vault.exists()
    if not exists and args.command != "add":
        print(f"No vault at {args.vault}. Create one with the 'add' command.", file=sys.stderr)
        return 1
    try:
        passphrase = read_secret(args.passphrase_file, args.passphrase_env, "Vault passphrase: ",
                                 confirm=not exists)
        if not exists and len(passphrase) < 8:
            raise ValueError("use a vault passphrase of at least 8 characters")
        entries = json.loads(decrypt(args.vault.read_bytes(), passphrase))["entries"] \
            if exists else {}
        changed, text = run(args, entries)
        if changed:
            save(args.vault, {"entries": entries}, passphrase)
    except (ValueError, OSError, KeyError, UnicodeDecodeError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
