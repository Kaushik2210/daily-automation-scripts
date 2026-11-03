"""Show size, format and EXIF details (camera, date, location flag) for images."""
import argparse
import json
import sys
from pathlib import Path

from PIL import ExifTags, Image

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
WANTED = ["Make", "Model", "DateTimeOriginal", "DateTime", "Orientation", "Software",
          "ISOSpeedRatings", "ExposureTime", "FNumber", "FocalLength"]
GPS_IFD = 0x8825
EXIF_IFD = 0x8769


def read_exif(img):
    """Return {tag name: value} for the common EXIF fields (main and Exif IFDs)."""
    exif = img.getexif()
    merged = {**exif, **exif.get_ifd(EXIF_IFD)}
    named = {ExifTags.TAGS.get(tag, str(tag)): value for tag, value in merged.items()}
    return {name: str(named[name]) for name in WANTED if name in named}, bool(exif.get_ifd(GPS_IFD))


def describe(path):
    with Image.open(path) as img:
        exif, has_gps = read_exif(img)
        info = {
            "file": path.name,
            "format": img.format,
            "size": f"{img.width}x{img.height}",
            "mode": img.mode,
            "megapixels": round(img.width * img.height / 1e6, 2),
            "bytes": path.stat().st_size,
            "frames": getattr(img, "n_frames", 1),
            "has_gps": has_gps,
            "exif": exif,
        }
        dpi = img.info.get("dpi")
        if dpi:
            info["dpi"] = f"{round(dpi[0])}x{round(dpi[1])}"
    return info


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read image metadata.")
    parser.add_argument("paths", nargs="+", type=Path, help="image files or folders")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args(argv)

    files = []
    for path in args.paths:
        files.extend(sorted(p for p in path.iterdir() if p.suffix.lower() in EXTENSIONS)
                     if path.is_dir() else [path])
    reports, status = [], 0
    for path in files:
        try:
            reports.append(describe(path))
        except OSError as err:
            print(f"skip {path.name}: not an image I can read ({err})", file=sys.stderr)
            status = 1
    if args.json:
        print(json.dumps(reports, indent=2))
        return status
    for r in reports:
        print(f"{r['file']}  {r['format']} {r['size']} ({r['megapixels']} MP, {r['mode']}, "
              f"{r['bytes']} bytes, {r['frames']} frame(s))")
        for name, value in r["exif"].items():
            print(f"    {name}: {value}")
        if r["has_gps"]:
            print("    location data: PRESENT (GPS tags found)")
    print(f"{len(reports)} image(s).")
    return status


if __name__ == "__main__":
    sys.exit(main())
