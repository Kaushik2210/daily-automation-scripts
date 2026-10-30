# bulk-file-renamer

## Purpose
Rename many files in one folder using find/replace, a prefix or suffix, and optional sequence numbers. Stops before touching anything if two files would end up with the same name.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python bulk_file_renamer.py FOLDER [--pattern GLOB] [--find TEXT --replace TEXT]
                            [--prefix TEXT] [--suffix TEXT]
                            [--number --start N --digits N] [--apply]
```
It is a dry run by default. Add `--apply` to rename for real.

## Example
```bash
python bulk_file_renamer.py ./photos --pattern "*.jpg" --find IMG --replace trip --number
```
```
IMG_0041.jpg -> trip_0041_001.jpg
IMG_0042.jpg -> trip_0042_002.jpg
Would rename 2 file(s). Use --apply to do it.
```

## Notes
- Only files directly inside the folder are renamed, not subfolders.
- The file extension is never changed.
- Exit code 1 means a name collision was found and nothing was renamed.
