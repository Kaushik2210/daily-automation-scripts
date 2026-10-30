# empty-folder-cleaner

## Purpose
Find folders that contain nothing, or only other empty folders, and optionally delete them.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python empty_folder_cleaner.py FOLDER [--apply]
```
Dry run by default; pass `--apply` to remove folders.

## Example
```bash
python empty_folder_cleaner.py ./project
```
```
./project/build/cache
./project/build
./project/tmp
Would remove 3 empty folder(s). Use --apply to do it.
```

## Notes
- The folder you pass in is never removed, only what is inside it.
- Folders are listed deepest first so removal works in order.
- Hidden files count as content, so a folder holding only `.gitkeep` is not empty.
