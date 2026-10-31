# folder-size-history

## Purpose
Keep a running record of how big a folder is, so you can see what grows over time: downloads, caches, project builds. Each run adds one line to a CSV.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python folder_size_history.py FOLDER [--log FILE.csv] [--show]
```
Without `--show` it records the current size and then prints the history for that folder. With `--show` it only prints the history. Run it from a scheduler to build up a timeline.

## Example
```bash
python folder_size_history.py ~/Downloads --log sizes.csv
```
```
Recorded 3.4 GB in 812 file(s) at 2026-10-31 09:00:12.
2026-10-30 09:00:05      3.1 GB     790 files
2026-10-31 09:00:12      3.4 GB     812 files  (310.2 MB change)
```

## Notes
- The CSV has the columns `timestamp, folder, bytes, files`, so it opens in any spreadsheet.
- One log file can track several folders; the history shows one folder at a time.
- It only appends to the log you name and never touches the folder being measured.
