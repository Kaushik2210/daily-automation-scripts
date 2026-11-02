# file-hasher

## Purpose
Compute checksums for one file or a whole folder. Several algorithms are calculated in a single pass over each file, so hashing a big file with MD5, SHA-1 and SHA-256 costs one read.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python file_hasher.py PATH [PATH ...] [-a md5|sha1|sha256|sha512] [-r] [--sums]
```
Use `-a` more than once for several algorithms (default `sha256`). `--sums` prints `hash  file` lines like the `sha256sum` tool, which you can keep as a checksum list.

## Example
```bash
python file_hasher.py setup.zip -a md5 -a sha256
```
```
setup.zip
  md5    5d41402abc4b2a76b9719d911017c592
  sha256 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
```

## Notes
- Folders are listed non-recursively unless you pass `-r`.
- Unreadable files are reported on stderr and the exit code becomes 1.
- Pair it with `hash-checker` to verify downloads.
