# exif-stripper

## Purpose
Photos quietly carry extra information: the GPS position where they were taken, the camera and phone model, the exact time, and the editing software. Before you post a picture online, this tool shows what each photo reveals and saves clean copies with the pixels only. Orientation is applied first, so portrait photos still look right.

## Install
Needs Pillow 10.1 or newer:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python exif_stripper.py FOLDER [-o OUTDIR] [--quality 95] [--apply]
```
Dry run by default: it lists what would be removed from each photo and writes nothing. With `--apply` the clean copies go into `FOLDER/clean` (or `-o`); originals are never modified and existing copies are never overwritten.

## Example
```bash
python exif_stripper.py . --apply
```
```
{{OUTPUT}}
```

## Notes
- JPEG copies are re-encoded (default quality 95), which is visually near-identical but not bit-for-bit.
- Colour profiles are dropped too, so colours can shift slightly on wide-gamut photos.
- Use `image-metadata-reader` to look at a single photo's full metadata first.
