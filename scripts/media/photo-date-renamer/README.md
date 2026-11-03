# photo-date-renamer

## Purpose
Give photos meaningful, sortable names such as `2026-01-05_101500.jpg` based on when they were actually taken. The time comes from the photo's EXIF data; if a file has none, its modified date is used instead.

## Install
Needs Pillow:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python photo_date_renamer.py FOLDER [--format PATTERN] [--apply]
```
`--format` is a [strftime](https://strftime.org) pattern (default `%Y-%m-%d_%H%M%S`). Dry run by default; pass `--apply` to rename. Photos taken in the same second get `-2`, `-3` added.

## Example
```bash
python photo_date_renamer.py ./camera-roll
```
```
IMG_4021.JPG -> 2026-07-14_182209.jpg  (EXIF)
WhatsApp Image.jpeg -> 2026-07-15_090511.jpeg  (file date)
Would rename 2 photo(s). Use --apply to do it.
```

## Notes
- Extensions are lowercased. Files that already have the target name are left alone.
- A rename is skipped if a file with the new name already exists.
- Messaging apps often strip EXIF data, so those photos fall back to the file date.
