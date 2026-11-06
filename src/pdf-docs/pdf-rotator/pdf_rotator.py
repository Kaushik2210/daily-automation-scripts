"""Rotate all or some pages of a PDF, writing the result to a new file."""
import argparse
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError
from pypdf.generic import NameObject, NumberObject


def parse_ranges(text, total):
    """'1-3,5,8-' -> [1, 2, 3, 5, 8, ...total]; pages are 1-based."""
    pages = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        start_text, dash, end_text = part.partition("-")
        try:
            start = int(start_text) if start_text else 1
            end = (int(end_text) if end_text else total) if dash else start
        except ValueError:
            raise ValueError(f"'{part}' is not a page or range") from None
        if start < 1 or end > total or start > end:
            raise ValueError(f"'{part}' is outside the document's {total} page(s)")
        pages.extend(range(start, end + 1))
    if not pages:
        raise ValueError("no pages selected")
    return pages


def rotate(reader, angle, pages):
    """Return a PdfWriter with `pages` (1-based) turned clockwise by `angle` degrees."""
    chosen = set(pages)
    writer = PdfWriter()
    for number, page in enumerate(reader.pages, 1):
        if number in chosen:
            page.rotate(angle)
            page[NameObject("/Rotate")] = NumberObject(page.rotation % 360)  # keep it 0-359
        writer.add_page(page)
    return writer


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rotate pages of a PDF.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--angle", type=int, required=True, choices=[90, 180, 270],
                        help="degrees to turn clockwise")
    parser.add_argument("--pages", help="pages to rotate, e.g. 1-3,5 (default: all pages)")
    parser.add_argument("-o", "--output", type=Path,
                        help="result file (default: <name>_rotated.pdf)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the file (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")

    try:
        reader = PdfReader(str(args.file))
        total = len(reader.pages)
        pages = parse_ranges(args.pages, total) if args.pages else list(range(1, total + 1))
    except (PyPdfError, OSError) as err:
        print(f"Can't read {args.file.name}: {err}", file=sys.stderr)
        return 1
    except ValueError as err:
        parser.error(str(err))

    target = args.output or args.file.with_name(f"{args.file.stem}_rotated.pdf")
    print(f"{args.file.name}: rotate {len(pages)} of {total} page(s) by {args.angle} degrees")
    if not args.apply:
        print(f"Dry run: would write {target}. Use --apply to do it.")
        return 0
    if target.exists():
        print(f"{target} already exists; choose another name with -o.", file=sys.stderr)
        return 1
    with target.open("wb") as handle:
        rotate(reader, args.angle, pages).write(handle)
    print(f"Wrote {target}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
