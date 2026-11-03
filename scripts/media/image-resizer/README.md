# image-resizer

## Purpose
Shrink or enlarge photos and screenshots while keeping their proportions: by width, by height, to fit inside a box, or by a percentage.

## Install
Needs Pillow:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python image_resizer.py PATH [PATH ...] [--width PX] [--height PX] [--percent N]
                        [-o OUTDIR] [--apply]
```
`PATH` can be image files or folders. Give both `--width` and `--height` to fit the image inside that box. Dry run by default: it lists the new sizes. Pass `--apply` to write the resized copies to `OUTDIR` (default `resized`). Originals are never touched.

## Example
```bash
python image_resizer.py ./photos --width 800 -o small --apply
```
```
beach.jpg: 4032x3024 -> 800x600
sunset.jpg: 3000x2000 -> 800x533
Resized 2 image(s).
```

## Notes
- Supports PNG, JPG, WEBP, GIF (first frame only), BMP and TIFF.
- Files that aren't readable images are skipped with a message.
- Resizing uses the high-quality Lanczos filter; JPEG output is saved at quality 90.
