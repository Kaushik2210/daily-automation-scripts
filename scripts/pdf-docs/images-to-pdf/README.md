# images-to-pdf

## Purpose
Turn photos, scans or screenshots into one PDF, one image per page, in the order you give. Choose neat A4 pages with the picture centred, or pages that match each image's own size.

## Install
Needs Pillow (and `pypdf` only for the tests):
```bash
pip install -r requirements.txt
```

## Usage
```bash
python images_to_pdf.py IMAGE_OR_FOLDER [...] [--size a4|fit] [-o images.pdf] [--apply]
```
A folder contributes its images sorted by name; individual files keep the order you list them. Dry run by default: it lists the pages. Pass `--apply` to write the PDF. An existing output file is never overwritten.

## Example
```bash
python images_to_pdf.py "Holiday Photo 01.JPG" "Holiday Photo 02.JPG" logo.png -o album.pdf
```
```
Holiday Photo 01.JPG: 320x200
Holiday Photo 02.JPG: 300x200
logo.png: 240x120
3 page(s), a4 size
Dry run: would write album.pdf. Use --apply to do it.
```

## Notes
- Transparent images are flattened onto white, and photos are turned upright using their EXIF orientation.
- On A4 pages, wide images get landscape pages and tall ones portrait pages, with a small margin.
- Unreadable files are skipped with a message.
