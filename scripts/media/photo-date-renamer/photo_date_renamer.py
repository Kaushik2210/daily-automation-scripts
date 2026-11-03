"""Rename photos using the date and time they were taken (EXIF), falling back to the file date."""
import argparse
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic"}
EXIF_IFD = 0x8769
DATE_TAGS = (0x9003, 0x9004)  # DateTimeOriginal, DateTimeDigitized
MAIN_DATE_TAG = 0x0132        # DateTime


def parse_exif_date(text):
    try:
        return datetime.strptime(str(text).strip(), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def capture_time(path):
    """Return (datetime, source) where source is 'EXIF' or 'file date'."""
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            ifd = exif.get_ifd(EXIF_IFD)
            for tag in DATE_TAGS:
                if tag in ifd and (found := parse_exif_date(ifd[tag])):
                    return found, "EXIF"
            if MAIN_DATE_TAG in exif and (found := parse_exif_date(exif[MAIN_DATE_TAG])):
                return found, "EXIF"
    except OSError:
        pass
    return datetime.fromtimestamp(path.stat().st_mtime), "file date"


def plan_renames(files, pattern="%Y-%m-%d_%H%M%S"):
    """Return [(source, new_name, source_of_date)] with -2, -3 ... added to repeated names."""
    used, plan = {}, []
    for path in files:
        when, origin = capture_time(path)
        base = when.strftime(pattern)
        used[base] = used.get(base, 0) + 1
        name = base if used[base] == 1 else f"{base}-{used[base]}"
        plan.append((path, f"{name}{path.suffix.lower()}", origin))
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rename photos by their capture date.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--format", default="%Y-%m-%d_%H%M%S",
                        help="strftime pattern for the new name (default %%Y-%%m-%%d_%%H%%M%%S)")
    parser.add_argument("--apply", action="store_true",
                        help="really rename the files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    files = sorted(p for p in args.folder.iterdir() if p.suffix.lower() in EXTENSIONS)
    done = 0
    for path, new_name, origin in plan_renames(files, args.format):
        target = path.with_name(new_name)
        if target == path:
            continue
        if target.exists():
            print(f"skip {path.name}: {new_name} already exists")
            continue
        print(f"{path.name} -> {new_name}  ({origin})")
        if args.apply:
            path.rename(target)
        done += 1
    verb = "Renamed" if args.apply else "Would rename"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {done} photo(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
