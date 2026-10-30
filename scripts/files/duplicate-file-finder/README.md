# duplicate-file-finder

## Purpose
Find files with identical content anywhere under a folder. Files are grouped by size first, so only candidates of equal size get hashed. The script only reports; it never deletes anything.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python duplicate_file_finder.py FOLDER [--min-size BYTES]
```

## Example
```bash
python duplicate_file_finder.py ~/Documents --min-size 1024
```
```
Group 1 (20480 bytes each):
  /home/me/Documents/report.pdf
  /home/me/Documents/old/report copy.pdf
1 duplicate group(s), 20480 bytes could be reclaimed.
```

## Notes
- Symlinks are ignored.
- Unreadable files are skipped with a message on stderr.
- Read-only, so there is no `--apply` flag.
