# hash-checker

## Purpose
Confirm that a download is exactly what the publisher intended. Give it the file and the checksum from the website, and it tells you whether they match.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python hash_checker.py FILE EXPECTED [-a md5|sha1|sha256|sha512]
```
`EXPECTED` can be the hash itself, text like `sha256:<hash>`, or the path of a checksum file such as `ubuntu.iso.sha256`. The algorithm is guessed from the hash length unless you pass `-a`. The exit code is 0 on a match and 1 on a mismatch.

## Example
```bash
python hash_checker.py installer.iso 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
```
```
OK: installer.iso matches the expected sha256 hash.
```

## Notes
- Prefer SHA-256 or SHA-512. MD5 and SHA-1 only guard against accidents, not tampering.
- The comparison uses a constant-time check and ignores letter case.
- Read-only.
