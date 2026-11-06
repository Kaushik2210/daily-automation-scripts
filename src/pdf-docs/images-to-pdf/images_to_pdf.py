"""Combine images into a single PDF, one image per page."""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
DPI = 150
A4_PIXELS = (round(8.27 * DPI), round(11.69 * DPI))   # 1240 x 1754 at 150 dpi


def flatten(img):
    """RGB copy with transparency flattened onto white, rotated upright if the EXIF says so."""
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        base = Image.new("RGB", rgba.size, "white")
        base.paste(rgba, mask=rgba.getchannel("A"))
        return base
    return img.convert("RGB")


def to_a4(img, margin=0.04):
    """Place the image centred on a white A4 page (landscape if the image is wider than tall)."""
    width, height = A4_PIXELS if img.height >= img.width else A4_PIXELS[::-1]
    page = Image.new("RGB", (width, height), "white")
    box = (round(width * (1 - 2 * margin)), round(height * (1 - 2 * margin)))
    fitted = ImageOps.contain(img, box, Image.Resampling.LANCZOS)
    page.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
    return page


def build_pages(paths, size="a4"):
    pages = []
    for path in paths:
        with Image.open(path) as img:
            flat = flatten(img)
            pages.append(to_a4(flat) if size == "a4" else flat)
    return pages


def collect(inputs):
    files = []
    for item in inputs:
        if item.is_dir():
            files.extend(sorted(p for p in item.iterdir() if p.suffix.lower() in EXTENSIONS))
        else:
            files.append(item)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Combine images into one PDF.")
    parser.add_argument("images", nargs="+", type=Path, help="image files or folders (in order)")
    parser.add_argument("--size", choices=["a4", "fit"], default="a4",
                        help="a4 pages with the image centred, or pages sized to each image")
    parser.add_argument("-o", "--output", type=Path, default=Path("images.pdf"),
                        help="the PDF to create (default: images.pdf)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the PDF (default is a dry run)")
    args = parser.parse_args(argv)

    files = collect(args.images)
    if not files:
        parser.error("no images found")
    usable = []
    for path in files:
        try:
            with Image.open(path) as img:
                print(f"{path.name}: {img.width}x{img.height}")
            usable.append(path)
        except OSError as err:
            print(f"skip {path.name}: not an image I can read ({err})")
    if not usable:
        return 1
    print(f"{len(usable)} page(s), {args.size} size")
    if not args.apply:
        print(f"Dry run: would write {args.output}. Use --apply to do it.")
        return 0
    if args.output.exists():
        print(f"{args.output} already exists; choose another name with -o.", file=sys.stderr)
        return 1
    pages = build_pages(usable, args.size)
    pages[0].save(args.output, "PDF", save_all=True, append_images=pages[1:], resolution=DPI)
    print(f"Wrote {args.output}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
