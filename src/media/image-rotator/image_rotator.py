"""Rotate, flip or straighten images in bulk."""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
CLOCKWISE = {90: Image.Transpose.ROTATE_270, 180: Image.Transpose.ROTATE_180,
             270: Image.Transpose.ROTATE_90}
FLIPS = {"horizontal": Image.Transpose.FLIP_LEFT_RIGHT, "vertical": Image.Transpose.FLIP_TOP_BOTTOM}


def transform(img, rotate=0, flip=None, fix_orientation=False):
    """Apply EXIF straightening, then rotation (clockwise degrees), then a flip."""
    if fix_orientation:
        img = ImageOps.exif_transpose(img)
    if rotate:
        img = img.transpose(CLOCKWISE[rotate])
    if flip:
        img = img.transpose(FLIPS[flip])
    return img


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rotate or flip images in bulk.")
    parser.add_argument("paths", nargs="+", type=Path, help="image files or folders")
    parser.add_argument("--rotate", type=int, choices=sorted(CLOCKWISE),
                        help="rotate clockwise by this many degrees")
    parser.add_argument("--flip", choices=sorted(FLIPS), help="mirror the image")
    parser.add_argument("--fix-orientation", action="store_true",
                        help="turn photos upright using their EXIF orientation flag")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("rotated"),
                        help="folder for the results (default: rotated)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the images (default is a dry run)")
    args = parser.parse_args(argv)
    if not (args.rotate or args.flip or args.fix_orientation):
        parser.error("choose --rotate, --flip or --fix-orientation")

    files = []
    for path in args.paths:
        files.extend(sorted(p for p in path.iterdir() if p.suffix.lower() in EXTENSIONS)
                     if path.is_dir() else [path])
    done = 0
    for path in files:
        try:
            with Image.open(path) as img:
                result = transform(img, args.rotate or 0, args.flip, args.fix_orientation)
                print(f"{path.name}: {img.width}x{img.height} -> {result.width}x{result.height}")
                if args.apply:
                    args.outdir.mkdir(parents=True, exist_ok=True)
                    result.save(args.outdir / path.name)
            done += 1
        except OSError as err:
            print(f"skip {path.name}: not an image I can read ({err})")
    verb = "Saved" if args.apply else "Would save"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {done} image(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
