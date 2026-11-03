# image-rotator

## Purpose
Fix sideways photos or mirror a batch of images. Rotate clockwise by 90, 180 or 270 degrees, flip horizontally or vertically, or turn photos upright using the orientation flag the camera stored.

## Install
Needs Pillow:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python image_rotator.py PATH [PATH ...] [--rotate 90|180|270] [--flip horizontal|vertical]
                        [--fix-orientation] [-o OUTDIR] [--apply]
```
At least one of the three actions is required, and they can be combined. Dry run by default; pass `--apply` to write the results into `OUTDIR` (default `rotated`).

## Example
```bash
python image_rotator.py ./scans --rotate 90 --apply
```
```
page1.png: 2480x3508 -> 3508x2480
page2.png: 2480x3508 -> 3508x2480
Saved 2 image(s).
```

## Notes
- Rotation is clockwise.
- Originals are never overwritten; results go to the output folder.
- Pixel quality is preserved for 90 degree turns and flips (no resampling).
