"""Pack a folder of images into one sprite sheet plus a JSON map of where each frame sits."""
import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image

EXTENSIONS = {".png", ".gif", ".webp", ".jpg", ".jpeg", ".bmp"}


def layout(sizes, columns, padding=0):
    """sizes: [(w, h)]. Return (cell_w, cell_h, sheet_w, sheet_h, [(x, y)]) on a uniform grid."""
    cell_w, cell_h = max(w for w, _ in sizes), max(h for _, h in sizes)
    rows = -(-len(sizes) // columns)
    positions = [(padding + (i % columns) * (cell_w + padding),
                  padding + (i // columns) * (cell_h + padding)) for i in range(len(sizes))]
    sheet_w = padding + columns * (cell_w + padding)
    sheet_h = padding + rows * (cell_h + padding)
    return cell_w, cell_h, sheet_w, sheet_h, positions


def build(paths, columns, padding):
    """Return (sheet image, atlas dict, [unreadable names])."""
    frames, unreadable = [], []
    for path in paths:
        try:
            with Image.open(path) as img:
                frames.append((path.name, img.convert("RGBA")))
        except OSError:
            unreadable.append(path.name)
    if not frames:
        return None, {}, unreadable
    columns = min(columns or math.ceil(math.sqrt(len(frames))), len(frames))
    cell_w, cell_h, width, height, positions = layout([f.size for _, f in frames], columns, padding)
    sheet = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    atlas = {"cell": [cell_w, cell_h], "size": [width, height], "frames": {}}
    for (name, frame), (x, y) in zip(frames, positions, strict=True):
        x, y = x + (cell_w - frame.width) // 2, y + (cell_h - frame.height) // 2
        sheet.paste(frame, (x, y))
        atlas["frames"][name] = {"x": x, "y": y, "w": frame.width, "h": frame.height}
    return sheet, atlas, unreadable


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pack images into a sprite sheet.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--columns", type=int, default=0, help="frames per row (square-ish)")
    parser.add_argument("--padding", type=int, default=2, help="pixels between frames (2)")
    parser.add_argument("--name", default="spritesheet", help="output name without extension")
    parser.add_argument("--apply", action="store_true",
                        help="really write the files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    if args.columns < 0 or args.padding < 0:
        parser.error("--columns and --padding can't be negative")

    png_path = args.folder / f"{args.name}.png"
    json_path = args.folder / f"{args.name}.json"
    paths = sorted(p for p in args.folder.iterdir()
                   if p.suffix.lower() in EXTENSIONS and p != png_path)
    sheet, atlas, unreadable = build(paths, args.columns, args.padding)
    for name in unreadable:
        print(f"skip {name}: not an image I can read")
    if sheet is None:
        print("No images found.", file=sys.stderr)
        return 1
    print(f"{len(atlas['frames'])} frame(s), cell {atlas['cell'][0]}x{atlas['cell'][1]}, "
          f"sheet {sheet.width}x{sheet.height}")
    for name, spot in atlas["frames"].items():
        print(f"  {name:<24} at ({spot['x']}, {spot['y']}) {spot['w']}x{spot['h']}")
    if not args.apply:
        print(f"Dry run. Use --apply to write {png_path.name} and {json_path.name}.")
        return 0
    taken = [p.name for p in (png_path, json_path) if p.exists()]
    if taken:
        print(f"{' and '.join(taken)} already exists; use --name for a new one.", file=sys.stderr)
        return 1
    atlas["image"] = png_path.name
    sheet.save(png_path)
    json_path.write_text(json.dumps(atlas, indent=1) + "\n", encoding="utf-8")
    print(f"Saved {png_path.name} and {json_path.name} in {args.folder}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
