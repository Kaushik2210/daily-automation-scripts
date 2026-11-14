# palette-extractor

## Purpose
Pull the main colors out of a picture, for designing a matching website, choosing a theme or just seeing what a photo is made of. You get each color as a hex code and RGB value, how much of the image it covers, a plain-English name (navy, orange, beige...) and a small bar, ordered from the most to the least common. Transparent areas count as white.

## Install
Needs Pillow:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python palette_extractor.py IMAGE [-n 5] [--json] [--swatch strip.png]
```
`-n` sets how many colors to find (1-16, default 5). `--json` prints machine-readable output. `--swatch` also saves a strip image with the colors in proportion; it refuses to overwrite an existing file.

## Example
```bash
python palette_extractor.py palette-demo.png -n 4
```
```
{{OUTPUT}}
```

## Notes
- Colors are found by median-cut quantisation on a reduced copy of the image, so it is fast even for large photos.
- Gradients and photographs produce "average" colors rather than exact pixel values.
- Use `grayscale-converter` or `image-converter` to change the image itself.
