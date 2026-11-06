"""Split a PDF by page ranges, or into fixed-size parts (one page each by default)."""
import argparse
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError


def parse_ranges(text, total):
    """'1-3,5,8-' -> [1, 2, 3, 5, 8, ...total]. Pages are 1-based and must exist."""
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


def plan(total, pages_text=None, every=None):
    """Return [(file_suffix, [page numbers])] describing the files to create."""
    if pages_text:
        pages = parse_ranges(pages_text, total)
        label = "_".join(part.strip() for part in pages_text.split(",") if part.strip())
        return [(f"_pages_{label}", pages)]
    size = every or 1
    chunks = [list(range(i, min(i + size, total + 1))) for i in range(1, total + 1, size)]
    width = max(3, len(str(len(chunks))))
    return [(f"_part{n:0{width}d}", chunk) for n, chunk in enumerate(chunks, 1)]


def write_part(reader, pages, target):
    writer = PdfWriter()
    for number in pages:
        writer.add_page(reader.pages[number - 1])
    with target.open("wb") as handle:
        writer.write(handle)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Split a PDF into parts.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--pages", help="pages to extract into ONE file, e.g. 1-3,5,8-")
    parser.add_argument("--every", type=int, help="one file per N pages (1 = one per page)")
    parser.add_argument("-o", "--outdir", type=Path, help="folder for the results (default: same)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")
    if bool(args.pages) == bool(args.every):
        parser.error("choose exactly one of --pages or --every")
    if args.every is not None and args.every < 1:
        parser.error("--every must be at least 1")

    try:
        reader = PdfReader(str(args.file))
        total = len(reader.pages)
        parts = plan(total, args.pages, args.every)
    except (PyPdfError, OSError) as err:
        print(f"Can't read {args.file.name}: {err}", file=sys.stderr)
        return 1
    except ValueError as err:
        parser.error(str(err))

    outdir = args.outdir or args.file.parent
    for suffix, pages in parts:
        target = outdir / f"{args.file.stem}{suffix}.pdf"
        shown = f"{pages[0]}-{pages[-1]}" if len(pages) > 1 else str(pages[0])
        print(f"{target.name}  (page{'s' if len(pages) > 1 else ''} {shown} of {total})")
        if args.apply:
            outdir.mkdir(parents=True, exist_ok=True)
            write_part(reader, pages, target)
    verb = "Wrote" if args.apply else "Would write"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {len(parts)} file(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
