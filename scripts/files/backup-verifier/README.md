# backup-verifier

## Purpose
A backup you haven't checked is a hope, not a backup. This tool compares a source folder with its backup (another folder, or a `.zip`) by SHA-256 hash and tells you exactly which files are missing from the backup, which have different content, and which exist only in the backup. The exit code is 0 when every source file is safely in the backup and 1 when something is wrong, so you can run it from a script or schedule after every backup.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python backup_verifier.py SOURCE BACKUP [--quick] [--strict] [--exclude PATTERN ...] [--strip PREFIX]
```
`BACKUP` can be a folder or a `.zip`. A zip that holds everything inside one top-level folder (as `zip-archiver` makes) is matched automatically; use `--strip "prefix/"` for other layouts. `--quick` compares sizes only, which is fast but can't catch an edit that keeps the same size. Extra files in the backup are reported but don't fail the check unless you add `--strict`. The bookkeeping files of `incremental-backup` (`.backup-manifest.json` and `.history`) are ignored. Nothing is changed; the tool only reads.

## Example
```bash
python backup_verifier.py demo-project demo-backup
```
```
Compared 5 source file(s) with 5 in the backup by SHA-256.
Missing from the backup (1):
  LICENSE
Different in the backup (1):
  src/utils.js
Only in the backup (1):
  old-notes.log
PROBLEMS FOUND - this backup can't be trusted yet.
```

## Notes
- Hashing reads every file, so verifying a large backup takes time; `--quick` is a first pass.
- Symbolic links are skipped on both sides.
- A passing check proves the backup matches the source now, not that the source itself is intact.
