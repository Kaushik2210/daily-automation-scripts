# filename-normalizer

## Purpose
Turn awkward file names such as `My Holiday Photo (1).JPG` into predictable ones like `my_holiday_photo_1.jpg`.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python filename_normalizer.py FOLDER [-r] [--sep _|-] [--apply]
```
Dry run by default; pass `--apply` to rename.

## Example
```bash
python filename_normalizer.py ./scans --sep -
```
```
Scan 01 (final).PDF -> scan-01-final.pdf
Receipt #4.png -> receipt-4.png
Would rename 2 file(s). Use --apply to do it.
```

## Notes
- Names are lowercased, spaces and punctuation collapse into one separator, and extensions are lowercased.
- If the cleaned name already exists, the file is skipped rather than overwritten.
- Names that would become empty are called `file`.
