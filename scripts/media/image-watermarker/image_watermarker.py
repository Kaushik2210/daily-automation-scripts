"""Add a text watermark to every image in a folder."""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
POSITIONS = ["bottom-right", "bottom-left", "top-right", "top-left", "center"]


def load_font(pixels):
    try:
        return ImageFont.load_default(size=pixels)
    except (TypeError, OSError):  # older Pillow or no FreeType: a fixed-size font
        return ImageFont.load_default()


def place(position, image_size, text_size, margin):
    (width, height), (tw, th) = image_size, text_size
    x = margin if "left" in position else width - tw - margin
    y = margin if "top" in position else height - th - margin
    if position == "center":
        x, y = (width - tw) // 2, (height - th) // 2
    return max(0, x), max(0, y)


def watermark(path, text, position="bottom-right", opacity=50, size_percent=5):
    """Return the image with the text stamped on it (white with a dark shadow)."""
    with Image.open(path) as img:
        base = ImageOps.exif_transpose(img).convert("RGBA")
    font = load_font(max(10, base.width * size_percent // 100))
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    x, y = place(position, base.size, (right - left, bottom - top), max(6, base.width // 50))
    alpha = round(255 * opacity / 100)
    draw.text((x - left + 2, y - top + 2), text, font=font, fill=(0, 0, 0, alpha))
    draw.text((x - left, y - top), text, font=font, fill=(255, 255, 255, alpha))
    return Image.alpha_composite(base, layer)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Add a text watermark to a folder of images.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--text", required=True, help="the watermark text, e.g. '(c) Me 2026'")
    parser.add_argument("--position", choices=POSITIONS, default="bottom-right")
    parser.add_argument("--opacity", type=int, default=50, help="0-100 (50)")
    parser.add_argument("--size", type=int, default=5, help="text height as %% of width (5)")
    parser.add_argument("-o", "--outdir", type=Path, help="output folder (watermarked)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    if not 0 <= args.opacity <= 100 or not 1 <= args.size <= 50:
        parser.error("--opacity must be 0-100 and --size 1-50")

    outdir = args.outdir or args.folder / "watermarked"
    done = 0
    for path in sorted(p for p in args.folder.iterdir() if p.suffix.lower() in EXTENSIONS):
        target = outdir / path.name
        if target.exists():
            print(f"skip {path.name}: {target.name} already exists in {outdir}")
            continue
        try:
            result = watermark(path, args.text, args.position, args.opacity, args.size)
        except OSError as err:
            print(f"skip {path.name}: not an image I can read ({err})")
            continue
        print(f"{path.name} -> {target} ({result.width}x{result.height})")
        if args.apply:
            outdir.mkdir(parents=True, exist_ok=True)
            if path.suffix.lower() in (".jpg", ".jpeg"):
                result = result.convert("RGB")
            result.save(target)
        done += 1
    verb = "Watermarked" if args.apply else "Would watermark"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {done} image(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
