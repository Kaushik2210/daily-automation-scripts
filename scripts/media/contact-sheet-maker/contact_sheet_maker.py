"""Build one contact sheet (a grid of labelled thumbnails) from a folder of images."""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def load_font(pixels):
    try:
        return ImageFont.load_default(size=pixels)
    except (TypeError, OSError):
        return ImageFont.load_default()


def shorten(name, limit):
    return name if len(name) <= limit else name[:limit - 1] + "…"


def build_sheet(paths, columns, thumb, labels=True, background="white"):
    """Return (sheet image, [names of unreadable files])."""
    font = load_font(max(10, thumb // 12))
    label_h = font.size + 8 if labels and hasattr(font, "size") else (18 if labels else 0)
    pad = max(8, thumb // 16)
    tiles, unreadable = [], []
    for path in paths:
        try:
            with Image.open(path) as img:
                tiles.append((path.name, ImageOps.fit(
                    ImageOps.exif_transpose(img).convert("RGB"), (thumb, thumb),
                    Image.Resampling.LANCZOS)))
        except OSError:
            unreadable.append(path.name)
    rows = -(-len(tiles) // columns) or 1
    sheet = Image.new("RGB", (pad + columns * (thumb + pad), pad + rows * (thumb + label_h + pad)),
                      background)
    draw = ImageDraw.Draw(sheet)
    for number, (name, tile) in enumerate(tiles):
        x = pad + (number % columns) * (thumb + pad)
        y = pad + (number // columns) * (thumb + label_h + pad)
        sheet.paste(tile, (x, y))
        if labels:
            draw.text((x, y + thumb + 3), shorten(name, max(6, thumb // 7)), font=font,
                      fill="#333333")
    return sheet, unreadable


def main(argv=None):
    parser = argparse.ArgumentParser(description="Make a contact sheet from a folder of images.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--columns", type=int, default=4, help="thumbnails per row (4)")
    parser.add_argument("--thumb", type=int, default=160, help="thumbnail size in pixels (160)")
    parser.add_argument("--no-labels", action="store_true", help="leave out the file names")
    parser.add_argument("-o", "--output", type=Path,
                        help="the sheet to create (default: FOLDER/contact-sheet.png)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the sheet (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    if args.columns < 1 or args.thumb < 16:
        parser.error("--columns must be at least 1 and --thumb at least 16")

    output = args.output or args.folder / "contact-sheet.png"
    paths = sorted(p for p in args.folder.iterdir()
                   if p.suffix.lower() in EXTENSIONS and p.resolve() != output.resolve())
    if not paths:
        print("No images found.", file=sys.stderr)
        return 1
    sheet, unreadable = build_sheet(paths, args.columns, args.thumb, not args.no_labels)
    for name in unreadable:
        print(f"skip {name}: not an image I can read")
    count = len(paths) - len(unreadable)
    print(f"{count} image(s) in a grid of {args.columns} column(s): "
          f"{sheet.width}x{sheet.height} pixels -> {output}")
    if not args.apply:
        print("Dry run. Use --apply to create the sheet.")
        return 0
    if output.exists():
        print(f"{output} already exists; choose another name with -o.", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    print(f"Saved {output}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
