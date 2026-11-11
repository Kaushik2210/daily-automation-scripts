# folder-sync

## Purpose
Make one folder match another. This one-way sync copies new files and updated files from a source folder to a target folder, and can optionally delete files from the target that no longer exist in the source. The source is never changed. Each copy goes through a temporary file and is swapped in when complete, so an interrupted run can't leave a half-written file. By default it only shows the plan.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python folder_sync.py SOURCE TARGET [--delete] [--quick] [--exclude PATTERN ...] [--apply]
```
Without `--delete`, files that exist only in the target are listed with `?` and kept. With `--delete` they are listed with `-` and removed on `--apply`, and folders left empty are tidied away. By default files are compared by size and content hash, which is exact; `--quick` compares size and modified time (the source must be newer by more than 2 seconds) and is much faster on big trees. As a safeguard, `--delete` refuses to run when the source has no files at all, because that usually means a wrong path; add `--allow-empty` if you mean it. The two folders can't contain each other, and symbolic links are skipped.

## Example
```bash
python folder_sync.py sync-source sync-target --delete
```
```
sync-source -> sync-target: 1 to add, 1 to update, 1 only in the target (to delete).
  + docs/new-chapter.md
  ~ readme.txt
  - old-only.txt

Dry run - nothing changed. Add --apply to sync.
```

## Notes
- Add `--apply` to change the target. Without it nothing is written or deleted.
- This is a mirror, not a two-way sync: changes made only in the target are overwritten when the same file changes in the source.
- Deleted files don't go to the recycle bin; run without `--apply` first and read the list.
- On the website demo the sync happens in your browser's temporary folder.
