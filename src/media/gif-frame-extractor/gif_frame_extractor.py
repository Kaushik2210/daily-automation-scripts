"""Save every frame of an animated GIF as a separate image."""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageSequence


def frame_info(path):
    """Return a list of (index, duration_ms) for each frame of the animation."""
    with Image.open(path) as img:
        return [(i, frame.info.get("duration", 0))
                for i, frame in enumerate(ImageSequence.Iterator(img))]


def frame_name(stem, index, total, fmt="png"):
    width = max(3, len(str(total)))
    return f"{stem}_frame{index + 1:0{width}d}.{fmt}"


def extract(path, outdir, fmt="png", apply=False):
    """Write each frame (when apply is True) and return the list of file names."""
    names = []
    with Image.open(path) as img:
        total = getattr(img, "n_frames", 1)
        for index, frame in enumerate(ImageSequence.Iterator(img)):
            name = frame_name(path.stem, index, total, fmt)
            names.append(name)
            if apply:
                outdir.mkdir(parents=True, exist_ok=True)
                rgb = frame.convert("RGB") if fmt in ("jpg", "jpeg") else frame.convert("RGBA")
                rgb.save(outdir / name)
    return names


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract the frames of an animated GIF.")
    parser.add_argument("gif", type=Path)
    parser.add_argument("--format", choices=["png", "jpg", "webp"], default="png",
                        help="image format for the frames (png)")
    parser.add_argument("-o", "--outdir", type=Path,
                        help="folder for the frames (default: <name>_frames)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the frames (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.gif.is_file():
        parser.error(f"not a file: {args.gif}")

    try:
        info = frame_info(args.gif)
    except OSError as err:
        print(f"Can't read {args.gif.name} as an image: {err}", file=sys.stderr)
        return 1
    total_ms = sum(d for _, d in info)
    print(f"{args.gif.name}: {len(info)} frame(s), {total_ms} ms in total")
    outdir = args.outdir or args.gif.with_name(f"{args.gif.stem}_frames")
    names = extract(args.gif, outdir, args.format, args.apply)
    for name, (_, duration) in zip(names, info, strict=True):
        print(f"  {name}  ({duration} ms)")
    verb = "Wrote" if args.apply else "Would write"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {len(names)} frame(s) to {outdir}.{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
