"""Find near-duplicate images (resized, recompressed, brightened) with perceptual hashes."""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def dhash(path, size=8):
    """A difference hash: one bit per pixel, set when it is brighter than its right neighbour."""
    with Image.open(path) as img:
        small = ImageOps.exif_transpose(img).convert("L").resize(
            (size + 1, size), Image.Resampling.LANCZOS)
        width, height, pixels = small.width, small.height, small.tobytes()
        meta = (img.width, img.height)
    bits = 0
    for y in range(height):
        for x in range(width - 1):
            bits = (bits << 1) | (pixels[y * width + x] > pixels[y * width + x + 1])
    return bits, meta


def distance(a, b):
    return (a ^ b).bit_count()


def group_similar(hashes, threshold):
    """hashes: {name: bits}. Return groups (lists of names, size >= 2) of similar images."""
    names = sorted(hashes)
    parent = {name: name for name in names}

    def find(name):
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    for i, first in enumerate(names):
        for second in names[i + 1:]:
            if distance(hashes[first], hashes[second]) <= threshold:
                parent[find(second)] = find(first)
    groups = {}
    for name in names:
        groups.setdefault(find(name), []).append(name)
    return [members for members in groups.values() if len(members) > 1]


def collect(folder, recursive):
    pattern = folder.rglob("*") if recursive else folder.iterdir()
    return sorted(p for p in pattern if p.is_file() and p.suffix.lower() in EXTENSIONS)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find near-duplicate images.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--threshold", type=int, default=6,
                        help="most differing bits (out of 64) to still count as similar (6)")
    parser.add_argument("-r", "--recursive", action="store_true", help="include subfolders")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    if not 0 <= args.threshold <= 32:
        parser.error("--threshold must be between 0 and 32")

    hashes, info = {}, {}
    for path in collect(args.folder, args.recursive):
        name = str(path.relative_to(args.folder))
        try:
            hashes[name], dims = dhash(path)
        except OSError as err:
            print(f"skip {name}: not an image I can read ({err})")
            continue
        info[name] = (dims, path.stat().st_size)
    groups = group_similar(hashes, args.threshold)
    for number, members in enumerate(groups, 1):
        best = max(members, key=lambda n: (info[n][0][0] * info[n][0][1], info[n][1]))
        print(f"Group {number}: {len(members)} similar images (largest marked *)")
        for name in members:
            (width, height), size = info[name]
            gap = distance(hashes[name], hashes[best])
            mark = "*" if name == best else " "
            print(f" {mark} {name:<28} {width}x{height}  {size / 1024:.1f} KB  "
                  f"{'(reference)' if name == best else f'{gap} bit(s) different'}")
    duplicates = sum(len(g) - 1 for g in groups)
    print(f"\nChecked {len(hashes)} image(s): {len(groups)} group(s), "
          f"{duplicates} possible duplicate(s). Nothing was changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
