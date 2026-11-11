# sync-conflict-finder

## Purpose
Cloud sync tools quietly leave extra copies when two devices change the same file at once, and nobody notices until something goes wrong. This tool scans a synced folder for those conflict copies - Dropbox and Nextcloud "conflicted copy" files, Syncthing `.sync-conflict-` files, and OneDrive's "name-COMPUTERNAME" copies - then compares each one with its original and tells you whether it is identical (safe to delete), different (worth a look) or an orphan (the original is gone). It only reports; it never deletes or moves anything.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python sync_conflict_finder.py FOLDER [--loose] [--exclude PATTERN ...]
```
The exit code is 1 when conflict copies exist and 0 when the folder is clean, so a scheduled job can alert you. OneDrive-style copies are only reported when the original file is in the same folder and the suffix looks like a computer name, to avoid false alarms on names like `summary-report.txt`. Add `--loose` to also report numbered copies such as `photo (1).jpg` (made by Google Drive and many browsers) when `photo.jpg` exists; this can flag legitimate files, which is why it's off by default. Symbolic links are skipped.

## Example
```bash
python sync_conflict_finder.py cloud
```
```
5 conflict copy/copies found in cloud:

[IDENTICAL] budget-DESKTOP-4F2K9.xlsx
    OneDrive-style (computer name added); original: budget.xlsx
    same content as the original - safe to delete
[DIFFERENT] notes (Kaushik's conflicted copy 2026-11-03).txt
    Dropbox/Nextcloud conflicted copy; original: notes.txt
    differs from the original (44 B vs 45 B, copy is same age) - compare before deleting
[DIFFERENT] notes (conflicted copy 2026-11-02).txt
    Dropbox/Nextcloud conflicted copy; original: notes.txt
    differs from the original (25 B vs 45 B, copy is same age) - compare before deleting
[ORPHAN] orphan (conflicted copy 2026-10-01).txt
    Dropbox/Nextcloud conflicted copy; original: orphan.txt
    the original file is gone, so this copy may be the only one
[DIFFERENT] plan.sync-conflict-20261104-101500-ABCDEFG.md
    Syncthing conflict; original: plan.md
    differs from the original (25 B vs 7 B, copy is same age) - compare before deleting

1 identical, 3 different, 1 without an original. Nothing was changed or deleted.
```

## Notes
- "Different" copies need a human: open both files, keep what you want, then delete the other by hand.
- Comparison is by content hash, so it is exact but reads both files.
- Run it after a long offline period or a reinstall, when conflicts are most likely.
