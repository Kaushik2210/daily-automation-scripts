"""Show a PDF's title, author, dates, page count and page size."""
import argparse
import json
import sys
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

SIZES_MM = {"A3": (297, 420), "A4": (210, 297), "A5": (148, 210), "Letter": (216, 279),
            "Legal": (216, 356), "Tabloid": (279, 432)}
PT_PER_MM = 72 / 25.4


def paper_name(width_pt, height_pt):
    """Name the page size (A4, Letter ...) if it matches within 3 mm, in either orientation."""
    w, h = sorted((width_pt / PT_PER_MM, height_pt / PT_PER_MM))
    for name, (sw, sh) in SIZES_MM.items():
        if abs(w - sw) <= 3 and abs(h - sh) <= 3:
            return name
    return "custom"


def describe(path):
    reader = PdfReader(str(path))
    info = {"file": path.name, "bytes": path.stat().st_size, "encrypted": reader.is_encrypted}
    if reader.is_encrypted:
        return info
    meta = reader.metadata
    first = reader.pages[0] if reader.pages else None
    info.update({
        "pages": len(reader.pages),
        "title": getattr(meta, "title", None),
        "author": getattr(meta, "author", None),
        "subject": getattr(meta, "subject", None),
        "creator": getattr(meta, "creator", None),
        "producer": getattr(meta, "producer", None),
        "created": str(meta.creation_date) if meta and meta.creation_date else None,
        "modified": str(meta.modification_date) if meta and meta.modification_date else None,
    })
    if first is not None:
        w, h = float(first.mediabox.width), float(first.mediabox.height)
        info["page_size"] = f"{w / PT_PER_MM:.0f} x {h / PT_PER_MM:.0f} mm ({paper_name(w, h)})"
    return info


def main(argv=None):
    parser = argparse.ArgumentParser(description="Show PDF metadata.")
    parser.add_argument("files", nargs="+", type=Path, help="PDF files")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args(argv)

    reports, status = [], 0
    for path in args.files:
        try:
            reports.append(describe(path))
        except (PyPdfError, OSError) as err:
            print(f"{path.name}: can't read it ({err})", file=sys.stderr)
            status = 1
    if args.json:
        print(json.dumps(reports, indent=2))
        return status
    for info in reports:
        print(info["file"])
        for key, value in info.items():
            if key != "file" and value not in (None, ""):
                print(f"  {key.replace('_', ' '):<10} {value}")
    return status


if __name__ == "__main__":
    sys.exit(main())
