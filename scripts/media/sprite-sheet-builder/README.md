# sprite-sheet-builder

## Purpose
Combine many small images into one picture (a sprite sheet) plus a JSON file saying where each one sits. Game engines and websites load one image instead of dozens, which is faster, and the JSON "atlas" tells your code the x, y, width and height of every frame. Frames of different sizes are centred in equal-sized cells on a tidy grid.

## Install
Needs Pillow:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python sprite_sheet_builder.py FOLDER [--columns N] [--padding 2] [--name spritesheet] [--apply]
```
Frames are packed in file-name order, so name them `frame-01.png`, `frame-02.png`... for animations. By default the grid is as square as possible. Dry run by default: it prints the layout. With `--apply` it writes `NAME.png` and `NAME.json` into the folder and refuses to overwrite earlier ones (use `--name` for a new sheet).

## Example
```bash
python sprite_sheet_builder.py sprites/ --columns 3 --apply
```
```
{{OUTPUT}}
```

## Notes
- Transparency is kept, so use PNG frames for sprites.
- A sheet from an earlier run is never packed into the next one.
- Use `contact-sheet-maker` for a labelled preview grid instead of a sheet for programs.
