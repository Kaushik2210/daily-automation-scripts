# image-watermarker

## Purpose
Stamp a text watermark (a copyright line, a name, "DRAFT") onto every image in a folder. The text is white with a soft dark shadow so it stays readable on both light and dark pictures, and you control the corner, size and transparency.

## Install
Needs Pillow 10.1 or newer:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python image_watermarker.py FOLDER --text "(c) Me 2026" [--position bottom-right] [--opacity 50] [--size 5] [-o OUTDIR] [--apply]
```
`--position` is one of `bottom-right`, `bottom-left`, `top-right`, `top-left` or `center`. `--size` is the text height as a percentage of the image width. Dry run by default; `--apply` writes the marked copies into `FOLDER/watermarked` (or `-o`) and never overwrites a file.

## Example
```bash
python image_watermarker.py . --text "(c) Kaushik 2026" --position bottom-left --apply
```
```
{{OUTPUT}}
```

## Notes
- Originals are never touched; JPEG results are saved without transparency.
- A watermark deters casual copying but can be cropped out; it is not protection.
- Use `contact-sheet-maker` to review a whole folder of results at a glance.
