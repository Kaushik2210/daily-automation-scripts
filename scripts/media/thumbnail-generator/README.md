# thumbnail-generator

## Purpose
Create small preview versions of every image in a folder, for galleries, websites or quick browsing. Photos taken in portrait mode are turned the right way up first.

## Install
Needs Pillow:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python thumbnail_generator.py FOLDER [--size PX] [--square] [--suffix TEXT] [-o OUTDIR] [--apply]
```
`--size` is the longest side (default 200). `--square` crops each thumbnail to an exact square. Dry run by default; pass `--apply` to write the files into `FOLDER/thumbs` (or `-o`).

## Example
```bash
python thumbnail_generator.py ./photos --size 160 --square --apply
```
```
beach_01.jpg -> beach_01_thumb.jpg (160x160)
sunset.jpg -> sunset_thumb.jpg (160x160)
Created 2 thumbnail(s) in photos/thumbs.
```

## Notes
- Without `--square` the aspect ratio is kept and small images are never enlarged.
- Unreadable files are skipped with a message.
- Originals are never changed.
