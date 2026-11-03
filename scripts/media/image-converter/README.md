# image-converter

## Purpose
Change images from one format to another, for example PNG screenshots to smaller JPGs, or JPGs to modern WEBP. Transparent PNGs are flattened onto white when saved as JPG, since JPG can't store transparency.

## Install
Needs Pillow:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python image_converter.py PATH [PATH ...] --to png|jpg|webp|gif|bmp|tiff
                          [--quality N] [-o OUTDIR] [--apply]
```
Dry run by default: it lists what would be converted. Pass `--apply` to write the new files into `OUTDIR` (default `converted`). The originals are kept.

## Example
```bash
python image_converter.py ./shots --to webp --quality 80 --apply
```
```
login.png -> login.webp
home.png -> home.webp
Converted 2 image(s).
```

## Notes
- Files already in the target format are skipped.
- `--quality` applies to JPG and WEBP.
- Animated GIFs convert to their first frame in other formats.
