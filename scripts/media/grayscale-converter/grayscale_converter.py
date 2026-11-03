"""Convert a folder of images to grayscale (black and white)."""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def to_grayscale(img, contrast=False):
    """Return a grayscale copy that keeps any transparency; optionally stretch the contrast."""
    has_alpha = img.mode in ("RGBA", "LA") or "transparency" in img.info
    source = img.convert("RGBA") if has_alpha else img
    gray = ImageOps.grayscale(source)
    if contrast:
        gray = ImageOps.autocontrast(gray)
    if has_alpha:
        gray = Image.merge("LA", (gray, source.getchannel("A")))
    return gray


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert images to grayscale.")
    parser.add_argument("paths", nargs="+", type=Path, help="image files or folders")
    parser.add_argument("--contrast", action="store_true", help="also stretch the contrast")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("grayscale"),
                        help="folder for the results (default: grayscale)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the images (default is a dry run)")
    args = parser.parse_args(argv)

    files = []
    for path in args.paths:
        files.extend(sorted(p for p in path.iterdir() if p.suffix.lower() in EXTENSIONS)
                     if path.is_dir() else [path])
    done = 0
    for path in files:
        try:
            with Image.open(path) as img:
                gray = to_grayscale(img, args.contrast)
                print(f"{path.name} -> {args.outdir.name}/{path.name} ({gray.mode})")
                if args.apply:
                    args.outdir.mkdir(parents=True, exist_ok=True)
                    gray.save(args.outdir / path.name)
            done += 1
        except OSError as err:
            print(f"skip {path.name}: not an image I can read ({err})")
    verb = "Converted" if args.apply else "Would convert"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {done} image(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
