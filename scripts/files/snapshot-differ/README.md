# snapshot-differ

## Purpose
See exactly what changed in a folder between two points in time. Take a snapshot (a small JSON file listing every file with its size and SHA-256 hash) and compare it with the folder today, or with another snapshot. The report shows files that were added, removed, changed, and moved or renamed (matched by identical content), plus how much the total size changed. It's the fast answer to "what did that installer or sync tool just do to my folder?".

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python snapshot_differ.py snapshot FOLDER --out before.json [--exclude PATTERN ...] [--quick]
python snapshot_differ.py compare before.json FOLDER
python snapshot_differ.py compare before.json after.json
python snapshot_differ.py compare OLD_FOLDER NEW_FOLDER
```
`compare` takes any mix of folders and snapshot files. The exit code is 1 when there are differences and 0 when the snapshots match, which makes it easy to use in scripts. `--quick` records sizes only, which is much faster for huge folders but can't see an edit that keeps a file the same size (and can't detect moves). Snapshot files are new files; an existing one is never overwritten. Symbolic links are skipped.

## Example
```bash
python snapshot_differ.py compare snapshot-old.json snapshot-new.json
```
```
OLD: 5 file(s) (2026-11-01T09:00:00)   NEW: 5 file(s) (2026-11-08T09:00:00)
Added (1):
  + docs/guide.md
Removed (1):
  - docs/old.md
Changed (1):
  ~ src/app.js
3 unchanged. Size change: -6 B.
```

## Notes
- Snapshots record file contents only by hash; they don't store the files themselves.
- Empty folders and permissions aren't tracked.
- Pair it with `incremental-backup` or `folder-sync` to audit what a run changed.
