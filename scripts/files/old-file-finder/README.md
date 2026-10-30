# old-file-finder

## Purpose
List files that have not been modified in a given number of days, oldest first. Handy before a cleanup or an archive run.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python old_file_finder.py FOLDER [--days N]
```
The default threshold is 365 days.

## Example
```bash
python old_file_finder.py ~/Documents --days 730
```
```
2021-03-14  /home/me/Documents/taxes/2020.xlsx
2022-07-02  /home/me/Documents/draft-v1.docx
2 file(s) older than 730 days.
```

## Notes
- Uses the last-modified time, searches subfolders and ignores symlinks.
- Read-only. Combine with `folder-organizer` or a backup script if you want to act on the list.
