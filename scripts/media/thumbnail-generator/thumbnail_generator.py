"""Make thumbnails for every image in a folder."""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def thumbnail_name(path, suffix="_thumb"):
    return f"{path.stem}{suffix}{path.suffix}"


def make_thumbnail(path, size, square=False):
    """Return a thumbnail that fits in size x size; square=True crops to an exact square."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)  # respect the camera's rotation flag
        if square:
            return ImageOps.fit(img, (size, size), Image.Resampling.LANCZOS)
        copy = img.copy()
        copy.thumbnail((size, size), Image.Resampling.LANCZOS)  # never enlarges
        return copy


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create thumbnails for a folder of images.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--size", type=int, default=200, help="longest side in pixels (200)")
    parser.add_argument("--square", action="store_true", help="crop to exact squares")
    parser.add_argument("--suffix", default="_thumb", help="added to each file name (_thumb)")
    parser.add_argument("-o", "--outdir", type=Path, help="folder for thumbnails (default: thumbs)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the thumbnails (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    if args.size < 1:
        parser.error("--size must be at least 1")

    outdir = args.outdir or args.folder / "thumbs"
    done = 0
    for path in sorted(p for p in args.folder.iterdir() if p.suffix.lower() in EXTENSIONS):
        target = outdir / thumbnail_name(path, args.suffix)
        try:
            thumb = make_thumbnail(path, args.size, args.square)
        except OSError as err:
            print(f"skip {path.name}: not an image I can read ({err})")
            continue
        print(f"{path.name} -> {target.name} ({thumb.width}x{thumb.height})")
        if args.apply:
            outdir.mkdir(parents=True, exist_ok=True)
            if target.suffix.lower() in (".jpg", ".jpeg") and thumb.mode != "RGB":
                thumb = thumb.convert("RGB")
            thumb.save(target)
        done += 1
    verb = "Created" if args.apply else "Would create"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {done} thumbnail(s) in {outdir}.{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
