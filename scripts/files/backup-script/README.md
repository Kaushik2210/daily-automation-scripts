# backup-script

## Purpose
Make a quick, dated copy of the folders you care about. Each run copies a folder into its own timestamped backup folder (`project-20261110-093000`), keeping file dates, empty folders and the folder layout. It checks every copied file's size, builds the backup under a temporary name and only renames it when everything succeeded, so a failed run never leaves a half-finished backup that looks complete. By default it only shows what it would do.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python backup_script.py FOLDER [FOLDER ...] --dest BACKUPS [--exclude PATTERN ...] [--apply]
```
`--exclude` takes names or patterns such as `node_modules`, `*.tmp` or `docs/private/*` (repeat it for several). Symbolic links are skipped rather than followed. The backup folder can't be inside the folder being backed up. An existing backup is never overwritten; run it again a second later or pick another `--dest`. Pair it with `backup-rotator` to prune old backups and `backup-verifier` to check the copy.

## Example
```bash
python backup_script.py demo-project --dest backups-new --exclude LICENSE --now 2026-11-10T09:30:00
```
```
demo-project -> backups-new/demo-project-20261110-093000
  4 file(s), 681 B, 1 skipped
    would copy package.json
    would copy src/app.js
    would copy src/utils.js
    would copy tests/app.test.js

Dry run - nothing copied. Add --apply to make the backup.
```

## Notes
- Add `--apply` to make the copy. Without it nothing is written.
- Copies keep modification times but not permissions or owners on every platform.
- A backup on the same disk doesn't protect you from the disk failing; use `--dest` on another drive or a synced folder.
- On the website demo the copy is made in your browser's temporary folder.
