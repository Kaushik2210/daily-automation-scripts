# downloads-sorter

## Purpose
Keep a downloads folder under control by filing loose files into `YYYY-MM` folders based on when they were last modified.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python downloads_sorter.py [FOLDER] [--apply]
```
`FOLDER` defaults to `~/Downloads`. Dry run by default; pass `--apply` to move files.

## Example
```bash
python downloads_sorter.py ~/Downloads
```
```
invoice.pdf -> 2026-09/
installer.zip -> 2026-10/
Would move 2 file(s). Use --apply to do it.
```

## Notes
- Only loose top-level files move; existing folders and hidden files stay put.
- A file is skipped if a file with the same name is already in the target month.
- Re-running is safe: already sorted files are inside folders and are not touched.
