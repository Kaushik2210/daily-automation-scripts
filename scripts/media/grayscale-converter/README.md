# grayscale-converter

## Purpose
Turn colour images into black and white in bulk, for printing, document scans or a consistent look. Transparent areas stay transparent, and an optional contrast stretch makes flat-looking scans pop.

## Install
Needs Pillow:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python grayscale_converter.py PATH [PATH ...] [--contrast] [-o OUTDIR] [--apply]
```
Dry run by default: it lists what would be converted. Pass `--apply` to write the results into `OUTDIR` (default `grayscale`). Originals are never changed.

## Example
```bash
python grayscale_converter.py ./scans --contrast --apply
```
```
page1.png -> grayscale/page1.png (L)
logo.png -> grayscale/logo.png (LA)
Converted 2 image(s).
```

## Notes
- `L` means plain grayscale; `LA` means grayscale with an alpha (transparency) channel.
- Unreadable files are skipped with a message.
- Uses the standard luminance formula, so greens look brighter than blues, as the eye sees them.
