"""Compress images in bulk with a quality setting, keeping only results that are smaller."""
import argparse
import io
import sys
from pathlib import Path

from PIL import Image, ImageOps

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def compress(path, quality, max_side=0):
    """Return (bytes, width, height) of the recompressed image."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        if max_side:
            img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        suffix, buffer = path.suffix.lower(), io.BytesIO()
        if suffix in (".jpg", ".jpeg"):
            img.convert("RGB").save(buffer, "JPEG", quality=quality, optimize=True)
        elif suffix == ".webp":
            img.save(buffer, "WEBP", quality=quality)
        else:
            img.save(buffer, "PNG", optimize=True)
        return buffer.getvalue(), img.width, img.height


def human(size):
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compress a folder of images.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--quality", type=int, default=80, help="JPEG/WebP quality 1-95 (80)")
    parser.add_argument("--max-side", type=int, default=0,
                        help="also shrink images whose longest side is bigger (0 = keep size)")
    parser.add_argument("-o", "--outdir", type=Path, help="output folder (compressed)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    if not 1 <= args.quality <= 95:
        parser.error("--quality must be between 1 and 95")

    outdir = args.outdir or args.folder / "compressed"
    before = after = count = 0
    for path in sorted(p for p in args.folder.iterdir() if p.suffix.lower() in EXTENSIONS):
        target = outdir / path.name
        try:
            data, width, height = compress(path, args.quality, args.max_side)
        except OSError as err:
            print(f"skip {path.name}: not an image I can read ({err})")
            continue
        original = path.stat().st_size
        if len(data) >= original:
            print(f"keep {path.name}: already small ({human(original)}), not worth recompressing")
            continue
        if target.exists():
            print(f"skip {path.name}: {target.name} already exists in {outdir}")
            continue
        print(f"{path.name}: {human(original)} -> {human(len(data))} "
              f"(-{100 - 100 * len(data) // original}%) {width}x{height}")
        before, after, count = before + original, after + len(data), count + 1
        if args.apply:
            outdir.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    verb = "Compressed" if args.apply else "Would compress"
    saved = f", saving {human(before - after)}" if count else ""
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {count} image(s){saved}.{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
