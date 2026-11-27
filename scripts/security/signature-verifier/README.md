# signature-verifier

## Purpose
Check a GnuPG (PGP) signature on a download or a release file, and explain the result in plain
words: was the file changed, is the signer's key known, is it expired or revoked, and do you
actually trust that key. It can insist on a specific signing key, which is what makes a "good
signature" worth anything.

## Install
It uses the `gpg` program from GnuPG (install it from gnupg.org, your package manager, or Gpg4win
on Windows). No Python packages are needed.

## Usage
```
python signature_verifier.py release.tar.gz.asc release.tar.gz
python signature_verifier.py release.tar.gz.sig release.tar.gz --expect-fingerprint 0123456789ABCDEF0123456789ABCDEF01234567
python signature_verifier.py message.asc                          # a clear-signed or inline-signed file
python signature_verifier.py file.sig file --require-trust full --format json
python signature_verifier.py --from-status saved-gpg-output.txt
```

Exit code 0 means the signature was accepted, 1 means it wasn't, so it works in scripts.

- A **good signature** only proves the file matches that key. It doesn't prove who owns the key.
  Compare the printed fingerprint with one the author published somewhere you trust, or pass it as
  `--expect-fingerprint` (repeatable) and the check fails for any other key.
- `--require-trust marginal|full|ultimate` also requires you to have certified the key.
- If a file has several signatures, the worst result is reported, so a bad one can't hide behind a
  good one.
- Import the signer's public key first (`gpg --import key.asc`), otherwise the result is "can't
  check: key not in your keyring".
- `--homedir` and `--gpg` choose another GnuPG home folder or program.
- `--from-status` reads saved `gpg --status-fd 1 --verify ...` output, so you can review a result
  without gpg installed.

## Example
`--from-status gpg-status-good.txt --expect-fingerprint 0123456789ABCDEF0123456789ABCDEF01234567`

```
Signature: GOOD
  Signer:      Ada Lovelace <ada@example.com> (key 89ABCDEF01234567)
  Fingerprint: 0123 4567 89AB CDEF 0123 4567 89AB CDEF 0123 4567
  Signed on:   2025-11-24
  Key trust:   fully

Accepted.
```

## Notes
- It only reads the machine-readable status lines (`[GNUPG:] ...`) that gpg prints, never the
  free-text messages, which can be spoofed.
- It never imports, trusts or changes any key.
- The sample status output was written by hand and describes an invented key.
