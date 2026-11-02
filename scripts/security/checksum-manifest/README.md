# checksum-manifest

## Purpose
Prove that a folder hasn't changed. Create a list of SHA-256 checksums for every file, then verify the folder against that list later to see which files changed, went missing or were added. Good for backups, releases and archives.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python checksum_manifest.py FOLDER [--manifest FILE] [--apply]      # create
python checksum_manifest.py FOLDER [--manifest FILE] --verify       # check
```
Creating is a dry run by default; pass `--apply` to write the manifest (default `SHA256SUMS.txt` inside the folder). Verifying is read-only and exits 1 if anything changed or is missing.

## Example
```bash
python checksum_manifest.py ./release --apply
python checksum_manifest.py ./release --verify
```
```
CHANGED front/app.js
NEW     notes.txt
48 file(s) checked: 1 changed, 0 missing, 1 new.
```

## Notes
- The manifest uses the `sha256sum` layout (`hash  path`), so standard tools can verify it too.
- The manifest file itself is never listed in its own checksums.
- New files are reported but don't count as a failure.
