# extension-counter

## Purpose
Get a quick picture of what a folder tree contains: how many files of each type and how much space each type takes.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python extension_counter.py [FOLDER] [-n TOP] [--by-size]
```
Rows are sorted by file count unless `--by-size` is given.

## Example
```bash
python extension_counter.py ./project -n 3
```
```
extension      files         bytes
.py               41        120394
.md               12         48210
.json              7          9120
75 file(s), 5 extension(s)
```

## Notes
- Extensions are lowercased, so `.JPG` and `.jpg` are counted together.
- Files without an extension appear as `(none)`.
- The summary line counts all files, even when `-n` trims the table.
