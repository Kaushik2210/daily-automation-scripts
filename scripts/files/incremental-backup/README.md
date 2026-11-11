# incremental-backup

## Purpose
Back up a folder quickly by copying only what changed. The first run copies everything into the backup folder, which then mirrors your source. Later runs compare the source with a small record kept in the backup (`.backup-manifest.json`) and copy just the new and changed files. Nothing is ever deleted from the backup, and when a changed file is replaced its previous version is kept under `.history/<timestamp>/`, so a bad edit can't wipe out a good backup. By default it only shows the plan.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python incremental_backup.py FOLDER --dest BACKUP [--exclude PATTERN ...] [--hash] [--no-history] [--apply]
```
Changes are detected by size and modification time (with a 2-second tolerance for FAT drives and cloud folders); `--hash` compares file contents instead, which is slower but exact. Files you delete from the source stay in the backup. `--exclude` takes names or patterns such as `node_modules` or `*.tmp`. Symbolic links are skipped. The source and backup folders can't contain each other.

## Example
```bash
python incremental_backup.py demo-project --dest mirror --exclude LICENSE
```
```
4 file(s) in demo-project: 4 new, 0 changed, 0 unchanged (681 B to copy).
  + package.json
  + src/app.js
  + src/utils.js
  + tests/app.test.js

Dry run - nothing copied. Add --apply to back up these files.
```

## Notes
- Add `--apply` to copy. Without it nothing is written.
- The `.history` folder grows over time; `backup-rotator` can prune old backup folders, or delete old `.history` stamps by hand.
- Use `backup-verifier` to check the mirror against the source by hash.
- On the website demo the copy is made in your browser's temporary folder.
