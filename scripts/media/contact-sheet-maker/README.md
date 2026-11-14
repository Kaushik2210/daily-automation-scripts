# contact-sheet-maker

## Purpose
See a whole folder of pictures on one page. The tool crops every image to a square thumbnail, arranges them in a grid with the file name underneath, and saves a single contact sheet you can browse, print or send for approval. Photos shot in portrait mode are turned the right way up first.

## Install
Needs Pillow 10.1 or newer:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python contact_sheet_maker.py FOLDER [--columns 4] [--thumb 160] [--no-labels] [-o SHEET.png] [--apply]
```
Dry run by default: it reports the grid size and what it would create. With `--apply` it writes `FOLDER/contact-sheet.png` (or `-o`) and refuses to overwrite an existing file. The sheet is never counted as one of its own inputs, so you can re-run it safely after moving the old one away.

## Example
```bash
python contact_sheet_maker.py sprites/ --columns 3 --thumb 96 --apply
```
```
6 image(s) in a grid of 3 column(s): 320x252 pixels -> sprites\contact-sheet.png
Saved sprites\contact-sheet.png.
```

## Notes
- Thumbnails are cropped to squares so the grid stays tidy; originals are untouched.
- Unreadable files are skipped with a message. The exit code is 1 when there is nothing to show or the sheet already exists.
- Use `thumbnail-generator` if you want a separate small file per image instead.
