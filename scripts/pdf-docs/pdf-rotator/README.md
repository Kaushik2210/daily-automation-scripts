# pdf-rotator

## Purpose
Fix sideways scans. Turn every page of a PDF, or just the ones you choose, by 90, 180 or 270 degrees clockwise. The result is saved as a new file and the original stays untouched.

## Install
Needs `pypdf`:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python pdf_rotator.py FILE.pdf --angle 90|180|270 [--pages 1-3,5] [-o OUTPUT] [--apply]
```
Without `--pages` every page is rotated. Dry run by default: it tells you what would happen. Pass `--apply` to write `<name>_rotated.pdf` (or the file you name with `-o`). An existing output file is never overwritten.

## Example
```bash
python pdf_rotator.py handbook.pdf --angle 90 --pages 2-3
```
```
handbook.pdf: rotate 2 of 5 page(s) by 90 degrees
Dry run: would write handbook_rotated.pdf. Use --apply to do it.
```

## Notes
- Rotation is clockwise and adds to any rotation a page already has.
- Page numbers start at 1; `3-` means page 3 to the end.
- The page content is not re-rendered, so there is no loss of quality.
