# backup-rotator

## Purpose
Stop old backups from filling your disk. Point the tool at the folder that collects your backups and tell it how many of the newest ones to keep; it lists which to keep and which to remove, oldest first, and how much space that frees. Backup age comes from the date in the name (`project-20261101-090000`, `backup_2026-11-01.zip`), falling back to the file's modified date. By default nothing is deleted.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python backup_rotator.py FOLDER --pattern "project-*" --keep 7 [--keep-monthly 6] [--apply]
```
`--pattern` is required and selects which entries are backups (files or folders directly inside `FOLDER`; patterns with slashes are refused), so anything else in the folder is never touched. `--keep` must be at least 1, so the newest backup can't be removed. `--keep-monthly M` additionally keeps the latest backup of each of the last M months, a simple way to hold on to older history cheaply. Symbolic links are removed themselves, never followed.

## Example
```bash
python backup_rotator.py backups --pattern "project-*" --keep 3
```
```
5 backup(s) match 'project-*': keeping 3, removing 2.
  keep    project-20261105-090000  (2026-11-05 09:00, newest 3)
  keep    project-20261104-090000  (2026-11-04 09:00, newest 3)
  keep    project-20261103-090000  (2026-11-03 09:00, newest 3)
  remove  project-20261102-090000  (2026-11-02 09:00)
  remove  project-20261101-090000  (2026-11-01 09:00)

Dry run - nothing deleted. --apply would free 58 B.
```

## Notes
- Add `--apply` to delete. Deleted backups don't go to the recycle bin, so read the list first.
- Works on any naming scheme that includes a date; names without one are ordered by modified time.
- Run it right after `backup-script` or `zip-archiver` to keep storage tidy.
- On the website demo the deletion happens in your browser's temporary folder.
