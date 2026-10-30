# folder-organizer

## Purpose
Tidy a messy folder by moving files into subfolders such as `images`, `documents` or `archives`, based on their extension.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python folder_organizer.py FOLDER [--by-extension] [--apply]
```
Dry run by default; pass `--apply` to move files.

## Example
```bash
python folder_organizer.py ~/Desktop
```
```
notes.txt -> documents/
holiday.jpg -> images/
setup.zip -> archives/
Would move 3 file(s). Use --apply to do it.
```

## Notes
- Only top-level files are moved; existing subfolders and hidden files are left alone.
- A file is skipped if the destination already has one with the same name.
- Unknown extensions go to `other`. Use `--by-extension` for one folder per extension.
