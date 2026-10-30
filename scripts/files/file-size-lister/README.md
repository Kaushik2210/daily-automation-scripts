# file-size-lister

## Purpose
Show which files in a folder take up the most space, with readable sizes and a total at the end.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python file_size_lister.py [FOLDER] [-r] [-n COUNT]
```
`FOLDER` defaults to the current directory. `-r` includes subfolders and `-n` sets how many rows to print (default 20).

## Example
```bash
python file_size_lister.py ~/Videos -r -n 3
```
```
   1.4 GB  trips/rome.mp4
 820.5 MB  trips/paris.mp4
  12.0 MB  intro.mov
212 file(s), 2.3 GB in total
```

## Notes
- Read-only.
- The total counts every file found, not just the rows shown.
