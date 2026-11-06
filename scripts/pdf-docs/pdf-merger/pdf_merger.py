"""Merge several PDF files into one, in the order you give them."""
import argparse
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError


def page_counts(paths):
    """Return [(path, pages)] and raise ValueError naming any file that isn't a readable PDF."""
    counts = []
    for path in paths:
        try:
            counts.append((path, len(PdfReader(str(path)).pages)))
        except (PyPdfError, OSError, ValueError) as err:
            raise ValueError(f"{path.name} isn't a readable PDF ({err})") from err
    return counts


def merge(paths, bookmarks=False):
    """Return a PdfWriter holding every page of every file, in order."""
    writer = PdfWriter()
    for path in paths:
        reader = PdfReader(str(path))
        start = len(writer.pages)
        for page in reader.pages:
            writer.add_page(page)
        if bookmarks:
            writer.add_outline_item(path.stem, start)
    return writer


def main(argv=None):
    parser = argparse.ArgumentParser(description="Merge PDF files into one.")
    parser.add_argument("files", nargs="+", type=Path, help="PDF files, in the order to merge")
    parser.add_argument("-o", "--output", type=Path, default=Path("merged.pdf"),
                        help="the merged file (default: merged.pdf)")
    parser.add_argument("--bookmarks", action="store_true",
                        help="add a bookmark for each source file")
    parser.add_argument("--apply", action="store_true",
                        help="really write the merged file (default is a dry run)")
    args = parser.parse_args(argv)
    for path in args.files:
        if not path.is_file():
            parser.error(f"not a file: {path}")

    try:
        counts = page_counts(args.files)
    except ValueError as err:
        print(err, file=sys.stderr)
        return 1
    for path, pages in counts:
        print(f"{path.name}: {pages} page(s)")
    total = sum(pages for _, pages in counts)
    if not args.apply:
        print(f"Dry run: would write {args.output} with {total} page(s). Use --apply to do it.")
        return 0
    if args.output.exists():
        print(f"{args.output} already exists; choose another name with -o.", file=sys.stderr)
        return 1
    with args.output.open("wb") as handle:
        merge(args.files, args.bookmarks).write(handle)
    print(f"Wrote {args.output} with {total} page(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
