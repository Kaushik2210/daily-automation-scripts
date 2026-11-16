"""Extract the dominant colors of an image as hex codes with their share of the picture."""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

NAMED = {"black": (0, 0, 0), "white": (255, 255, 255), "gray": (128, 128, 128),
         "red": (200, 30, 40), "orange": (240, 140, 30), "yellow": (245, 215, 60),
         "green": (50, 160, 70), "teal": (30, 150, 150), "blue": (40, 80, 200),
         "navy": (20, 40, 110), "purple": (130, 60, 170), "pink": (240, 130, 180),
         "brown": (130, 80, 45), "beige": (225, 205, 165)}


def color_name(rgb):
    return min(NAMED, key=lambda n: sum((a - b) ** 2 for a, b in zip(NAMED[n], rgb, strict=True)))


def extract(path, count=5):
    """Return [(rgb tuple, share 0..1)] sorted by share, using median-cut quantisation."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img).convert("RGBA")
        img.thumbnail((160, 160), Image.Resampling.NEAREST)
        flat = Image.new("RGB", img.size, (255, 255, 255))
        flat.paste(img, mask=img.getchannel("A"))
    quantised = flat.quantize(colors=count, method=Image.Quantize.MEDIANCUT,
                              dither=Image.Dither.NONE)
    palette = quantised.getpalette()
    total = flat.width * flat.height
    result = []
    for amount, index in quantised.getcolors():
        result.append((tuple(palette[index * 3:index * 3 + 3]), amount / total))
    return sorted(result, key=lambda item: -item[1])


def hex_code(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def swatch_image(colors, width=600, height=120):
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    left = 0
    for number, (rgb, share) in enumerate(colors):
        right = width if number == len(colors) - 1 else left + max(1, round(width * share))
        draw.rectangle((left, 0, right, height), fill=rgb)
        left = right
    return image


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find an image's dominant colors.")
    parser.add_argument("image", type=Path)
    parser.add_argument("-n", "--colors", type=int, default=5, help="how many colors (5)")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument("--swatch", type=Path, help="also save a strip of the colors as an image")
    args = parser.parse_args(argv)
    if not 1 <= args.colors <= 16:
        parser.error("--colors must be between 1 and 16")
    if args.swatch and args.swatch.exists():
        parser.error(f"{args.swatch} already exists; pick another name")
    try:
        colors = extract(args.image, args.colors)
    except OSError as err:
        print(f"Can't read {args.image}: {err}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps([{"hex": hex_code(rgb), "rgb": list(rgb), "name": color_name(rgb),
                           "share": round(share, 4)} for rgb, share in colors], indent=1))
    else:
        for rgb, share in colors:
            bar = "#" * max(1, round(share * 30))
            print(f"{hex_code(rgb)}  rgb({rgb[0]:>3}, {rgb[1]:>3}, {rgb[2]:>3})  "
                  f"{share * 100:5.1f}%  {color_name(rgb):<7} {bar}")
    if args.swatch:
        swatch_image(colors).save(args.swatch)
        print(f"Saved swatch strip to {args.swatch}", file=sys.stderr if args.json else sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
