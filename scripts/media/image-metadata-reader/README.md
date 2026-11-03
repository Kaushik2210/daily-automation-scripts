# image-metadata-reader

## Purpose
See what is hidden inside an image file: dimensions, format, colour mode, resolution and, for photos, the EXIF details such as camera, capture date and orientation. It also warns when a photo carries GPS location data, which you may want to remove before sharing.

## Install
Needs Pillow:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python image_metadata_reader.py PATH [PATH ...] [--json]
```
`PATH` can be image files or folders.

## Example
```bash
python image_metadata_reader.py holiday.jpg
```
```
holiday.jpg  JPEG 4032x3024 (12.19 MP, RGB, 2481023 bytes, 1 frame(s))
    Make: Apple
    Model: iPhone 15
    DateTimeOriginal: 2026:07:14 18:22:09
    location data: PRESENT (GPS tags found)
1 image(s).
```

## Notes
- Read-only.
- The exit code is 1 if any file couldn't be read as an image.
- To strip location data from photos, see the `exif-stripper` tool planned later in this challenge.
