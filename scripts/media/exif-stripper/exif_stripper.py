"""Remove EXIF and location data from photos by saving clean copies."""
import argparse
import sys
from pathlib import Path

from PIL import ExifTags, Image, ImageOps

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
GPS_IFD = 0x8825


def describe(img):
    """Return a short list of the sensitive things this image carries."""
    exif = img.getexif()
    found = []
    if exif.get_ifd(GPS_IFD):
        found.append("GPS location")
    names = {ExifTags.TAGS.get(tag, tag): value for tag, value in exif.items()}
    if names.get("Make") or names.get("Model"):
        found.append("camera " + " ".join(str(names[k]).strip() for k in ("Make", "Model")
                                           if names.get(k)))
    if names.get("DateTime"):
        found.append(f"date {names['DateTime']}")
    if names.get("Software"):
        found.append(f"software {names['Software']}")
    found += [f"{key} block" for key in ("comment", "xmp") if key in img.info]
    return found


def clean_copy(img):
    """A new image with the same pixels and nothing else (orientation is applied first)."""
    img = ImageOps.exif_transpose(img)
    clean = Image.frombytes(img.mode, img.size, img.tobytes())
    if img.mode == "P" and img.getpalette():
        clean.putpalette(img.getpalette())
    return clean


def main(argv=None):
    parser = argparse.ArgumentParser(description="Remove EXIF/GPS data from photos.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("-o", "--outdir", type=Path, help="folder for the copies (default: clean)")
    parser.add_argument("--quality", type=int, default=95, help="JPEG quality of the copies (95)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    outdir = args.outdir or args.folder / "clean"
    with_data = total = 0
    for path in sorted(p for p in args.folder.iterdir() if p.suffix.lower() in EXTENSIONS):
        target = outdir / path.name
        try:
            with Image.open(path) as img:
                found = describe(img)
                if target.exists():
                    print(f"skip {path.name}: {target.name} already exists in {outdir}")
                    continue
                clean = clean_copy(img)
        except OSError as err:
            print(f"skip {path.name}: not an image I can read ({err})")
            continue
        total += 1
        with_data += bool(found)
        print(f"{path.name}: " + ("removes " + ", ".join(found) if found else "no metadata found"))
        if args.apply:
            outdir.mkdir(parents=True, exist_ok=True)
            if path.suffix.lower() in (".jpg", ".jpeg"):
                clean.convert("RGB").save(target, quality=args.quality)
            else:
                clean.save(target)
    verb = "Cleaned" if args.apply else "Would clean"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {total} photo(s); {with_data} carried metadata.{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
