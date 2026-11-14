# image-compressor

## Purpose
Shrink a whole folder of photos so they upload and load faster. Each JPEG/WebP is re-encoded at the quality you choose, PNGs are re-saved with maximum lossless compression, and large images can also be scaled down with `--max-side`. A file is only written when the result is actually smaller; otherwise it is reported as "already small" and left alone.

## Install
Needs Pillow:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python image_compressor.py FOLDER [--quality 80] [--max-side PX] [-o OUTDIR] [--apply]
```
Dry run by default: it works out the savings but writes nothing. With `--apply` the compressed copies go into `FOLDER/compressed` (or `-o`). Originals are never changed and existing results are never overwritten.

## Example
```bash
python image_compressor.py . --quality 40 --apply
```
```
gps-photo.jpg: 4.8 KB -> 1.8 KB (-62%) 320x220
Holiday Photo 01.JPG: 3.9 KB -> 1.9 KB (-53%) 320x200
Holiday Photo 02.JPG: 2.7 KB -> 958 B (-66%) 300x200
logo.png: 840 B -> 630 B (-25%) 240x120
keep palette-demo.png: already small (286 B), not worth recompressing
photo-portrait.jpg: 3.3 KB -> 1.5 KB (-54%) 300x200
Screenshot 2026-03-01 at 09.30.15.png: 386 B -> 313 B (-19%) 160x100
Screenshot 2026-03-02 at 14.05.00.png: 387 B -> 314 B (-19%) 160x100
Compressed 7 image(s), saving 8.9 KB.
```

## Notes
- Quality 70-85 is a good balance for photos; below 50 you will start to see blocky areas.
- Photos are turned the right way up using their rotation flag; other metadata such as camera details is dropped by the re-encode.
- Use `exif-stripper` if you only want to remove location data, and `image-resizer` for exact sizes.
