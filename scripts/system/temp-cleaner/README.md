# temp-cleaner

## Purpose
Free up space by deleting files that have sat untouched in a temp folder for a while.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python temp_cleaner.py [FOLDER ...] [--days N] [--apply]
```
With no folder it uses your system temp folder. Files must be older than `--days` (default 7). Dry run by default; pass `--apply` to delete.

## Example
```bash
python temp_cleaner.py --days 14
```
```
   3.2 MB  /tmp/build-cache.tmp
  41.0 KB  /tmp/session-9f2.log
Would delete 2 file(s), 3.2 MB. Use --apply to do it.
```

## Notes
- Only files are deleted, never folders, and symlinks are left alone.
- Files that are still in use are skipped and counted.
- It refuses to run on a drive root or your home folder, so a typo can't wipe your documents.
