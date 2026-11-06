"""Resize images by width, height or percentage, keeping the aspect ratio."""
import argparse
import sys
from pathlib import Path

from PIL import Image

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def target_size(size, width=None, height=None, percent=None):
    """New (width, height). With both width and height the image fits inside that box."""
    w, h = size
    if percent:
        scale = percent / 100
    elif width and height:
        scale = min(width / w, height / h)
    elif width:
        scale = width / w
    elif height:
        scale = height / h
    else:
        raise ValueError("give --width, --height or --percent")
    return max(1, round(w * scale)), max(1, round(h * scale))


def collect_images(paths):
    files = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(p for p in path.iterdir() if p.suffix.lower() in EXTENSIONS))
        else:
            files.append(path)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Resize images, keeping the aspect ratio.")
    parser.add_argument("paths", nargs="+", type=Path, help="image files or folders")
    parser.add_argument("--width", type=int, help="new width in pixels")
    parser.add_argument("--height", type=int, help="new height in pixels")
    parser.add_argument("--percent", type=float, help="scale by this percentage (50 = half size)")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("resized"),
                        help="folder for the results (default: resized)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the images (default is a dry run)")
    args = parser.parse_args(argv)
    if not (args.width or args.height or args.percent):
        parser.error("give --width, --height or --percent")

    done = 0
    for path in collect_images(args.paths):
        try:
            with Image.open(path) as img:
                new_size = target_size(img.size, args.width, args.height, args.percent)
                print(f"{path.name}: {img.width}x{img.height} -> {new_size[0]}x{new_size[1]}")
                if args.apply:
                    args.outdir.mkdir(parents=True, exist_ok=True)
                    img.resize(new_size, Image.Resampling.LANCZOS).save(args.outdir / path.name,
                                                                         quality=90)
            done += 1
        except OSError as err:
            print(f"skip {path.name}: not an image I can read ({err})")
    verb = "Resized" if args.apply else "Would resize"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {done} image(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
