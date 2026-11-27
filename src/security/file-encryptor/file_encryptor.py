"""Encrypt and decrypt files with a passphrase (scrypt + AES-256-GCM). Never overwrites a file."""
import argparse
import contextlib
import getpass
import hashlib
import os
import sys
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"DAS1"          # file format: MAGIC, log2(N), r, p, salt(16), nonce(12), ciphertext+tag
SCRYPT_LOG2 = 15
MAX_LOG2 = 20
HEADER = len(MAGIC) + 3 + 16 + 12


def derive_key(passphrase, salt, n_log2, r=8, p=1):
    return Scrypt(salt=salt, length=32, n=2**n_log2, r=r, p=p).derive(passphrase.encode())


def encrypt(data, passphrase):
    salt, nonce = os.urandom(16), os.urandom(12)
    header = MAGIC + bytes([SCRYPT_LOG2, 8, 1]) + salt + nonce
    return header + AESGCM(derive_key(passphrase, salt, SCRYPT_LOG2)).encrypt(nonce, data, header)


def decrypt(blob, passphrase):
    if len(blob) < HEADER + 16 or blob[:4] != MAGIC:
        raise ValueError("this isn't a file made by this tool")
    n_log2, r, p = blob[4], blob[5], blob[6]
    if not 4 <= n_log2 <= MAX_LOG2 or not 1 <= r <= 16 or not 1 <= p <= 4:
        raise ValueError("the file asks for unreasonable key settings; refusing to open it")
    try:
        key = derive_key(passphrase, blob[7:23], n_log2, r, p)
        return AESGCM(key).decrypt(blob[23:35], blob[HEADER:], blob[:HEADER])
    except InvalidTag:
        raise ValueError("wrong passphrase, or the file has been changed") from None


def get_passphrase(args, creating):
    if args.passphrase_file:
        lines = args.passphrase_file.read_text(encoding="utf-8").splitlines()
        secret = lines[0] if lines else ""
    elif os.environ.get(args.passphrase_env):
        secret = os.environ[args.passphrase_env]
    else:
        secret = getpass.getpass("Passphrase: ")
        if creating and getpass.getpass("Again: ") != secret:
            raise ValueError("the two passphrases didn't match")
    if not secret:
        raise ValueError("the passphrase can't be empty")
    if creating and len(secret) < 8:
        raise ValueError("use a passphrase of at least 8 characters")
    return secret


def target_for(source, mode, output_dir):
    folder = output_dir or source.parent
    if mode == "encrypt":
        return folder / (source.name + ".enc")
    name = source.name[:-4] if source.name.lower().endswith(".enc") else source.name + ".decrypted"
    return folder / name


def write_new(path, data):
    """Create `path` and fail if it already exists, so nothing is ever overwritten."""
    try:
        with path.open("xb") as handle:
            handle.write(data)
    except FileExistsError:
        raise ValueError(f"{path} already exists; it was left alone") from None
    except OSError:
        path.unlink(missing_ok=True)
        raise
    with contextlib.suppress(OSError):
        os.chmod(path, 0o600)


def process(source, mode, passphrase, output_dir, max_bytes):
    """Encrypt or decrypt one file. Returns the output path."""
    if not source.is_file():
        raise ValueError("not a file")
    if source.stat().st_size > max_bytes:
        raise ValueError(f"larger than {max_bytes // 1024 // 1024} MB (see --max-mb)")
    data = source.read_bytes()
    if mode == "encrypt":
        if data[:4] == MAGIC:
            raise ValueError("already encrypted by this tool")
        result = encrypt(data, passphrase)
    else:
        result = decrypt(data, passphrase)  # raises before anything is written
    target = target_for(source, mode, output_dir)
    write_new(target, result)
    return target


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Encrypt and decrypt files with a passphrase.")
    parser.add_argument("mode", choices=["encrypt", "decrypt"])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path,
                        help="write results here (default: next to each input)")
    parser.add_argument("--remove-original", action="store_true",
                        help="delete the input afterwards (needs --apply, checked first)")
    parser.add_argument("--apply", action="store_true",
                        help="really delete originals (without it --remove-original previews)")
    parser.add_argument("--max-mb", type=int, default=200,
                        help="skip files larger than this many MB (200)")
    parser.add_argument("--passphrase-file", type=Path, dest="passphrase_file",
                        help="file whose first line is the passphrase")
    parser.add_argument("--passphrase-env", default="FILE_ENCRYPTOR_PASSPHRASE", metavar="NAME",
                        help="environment variable holding the passphrase")
    args = parser.parse_args(argv)
    if args.max_mb < 1:
        parser.error("--max-mb must be at least 1")
    if args.output_dir and not args.output_dir.is_dir():
        parser.error(f"--output-dir {args.output_dir} is not a folder")
    try:
        passphrase = get_passphrase(args, creating=args.mode == "encrypt")
    except (ValueError, OSError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    failures = 0
    for source in args.files:
        try:
            original = source.read_bytes() if args.remove_original and source.is_file() else None
            target = process(source, args.mode, passphrase, args.output_dir, args.max_mb * 1024**2)
            print(f"{args.mode}ed  {source} -> {target}")
            if args.remove_original:
                # prove the result is good before offering to delete the input
                check = target.read_bytes()
                restored = decrypt(check, passphrase) if args.mode == "encrypt" else check
                if args.mode == "encrypt" and digest(restored) != digest(original):
                    raise ValueError("verification failed; the original was kept")
                if args.apply:
                    source.unlink()
                    print(f"removed   {source}")
                else:
                    print(f"would remove {source} (verified; add --apply to delete it)")
        except (ValueError, OSError) as err:
            failures += 1
            print(f"FAILED    {source}: {err}", file=sys.stderr)
    done = len(args.files) - failures
    print(f"\n{done} of {len(args.files)} file(s) {args.mode}ed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
