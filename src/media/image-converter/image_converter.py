"""Convert images between PNG, JPG, WEBP, GIF, BMP and TIFF."""
import argparse
import sys
from pathlib import Path

from PIL import Image

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
FORMATS = {"png": "PNG", "jpg": "JPEG", "webp": "WEBP", "gif": "GIF", "bmp": "BMP", "tiff": "TIFF"}


def prepare(img, fmt):
    """Make the image mode compatible with the target format."""
    if fmt in ("JPEG", "BMP") and img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))  # flatten transparency to white
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    if fmt == "JPEG" and img.mode != "RGB":
        return img.convert("RGB")
    return img


def convert(path, target_format, outdir, quality=90):
    """Convert one image; returns the output path."""
    out = outdir / f"{path.stem}.{'jpg' if target_format == 'JPEG' else target_format.lower()}"
    with Image.open(path) as img:
        prepare(img, target_format).save(out, target_format, quality=quality)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert images to another format.")
    parser.add_argument("paths", nargs="+", type=Path, help="image files or folders")
    parser.add_argument("--to", required=True, choices=sorted(FORMATS), help="target format")
    parser.add_argument("--quality", type=int, default=90, help="JPEG/WEBP quality 1-100 (90)")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("converted"),
                        help="folder for the results (default: converted)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the images (default is a dry run)")
    args = parser.parse_args(argv)

    fmt = FORMATS[args.to]
    files = []
    for path in args.paths:
        files.extend(sorted(p for p in path.iterdir() if p.suffix.lower() in EXTENSIONS)
                     if path.is_dir() else [path])
    done = 0
    for path in files:
        target = args.outdir / f"{path.stem}.{'jpg' if fmt == 'JPEG' else fmt.lower()}"
        if path.suffix.lower().lstrip(".") in (args.to, "jpeg" if args.to == "jpg" else args.to):
            print(f"skip {path.name}: already {args.to}")
            continue
        try:
            print(f"{path.name} -> {target.name}")
            if args.apply:
                args.outdir.mkdir(parents=True, exist_ok=True)
                convert(path, fmt, args.outdir, args.quality)
            done += 1
        except OSError as err:
            print(f"skip {path.name}: not an image I can read ({err})")
    verb = "Converted" if args.apply else "Would convert"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {done} image(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
