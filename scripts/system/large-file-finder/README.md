# large-file-finder

## Purpose
Track down the files eating your disk. Lists the biggest files under a folder with their last-modified date, and can skip folders such as `node_modules` or `.git`.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python large_file_finder.py [FOLDER] [-n COUNT] [--min-size SIZE] [--exclude NAME ...]
```
Sizes accept units: `500`, `10KB`, `50MB`, `1.5GB`. `--exclude` can be repeated.

## Example
```bash
python large_file_finder.py ~/Projects -n 3 --min-size 50MB --exclude node_modules
```
```
   1.8 GB  2026-08-02  /home/me/Projects/video/final.mov
 612.4 MB  2026-09-14  /home/me/Projects/data/dump.sql
  88.0 MB  2026-10-01  /home/me/Projects/app/build.zip
3 file(s) listed, 2.5 GB together (scanned 14:03:09).
```

## Notes
- Read-only; it never deletes anything.
- Symlinks and unreadable files are skipped.
- Only the top results are kept in memory, so it copes with very large folders.
