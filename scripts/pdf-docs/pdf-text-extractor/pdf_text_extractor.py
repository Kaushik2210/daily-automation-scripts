"""Extract the text from PDF files, to the screen or into .txt files."""
import argparse
import sys
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError


def extract(path, markers=False):
    """Return (text, page_count). Pages are separated by a blank line, or by a marker line."""
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise ValueError("password protected")
    parts = []
    for number, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        parts.append(f"--- page {number} ---\n{text}" if markers else text)
    return "\n\n".join(parts), len(reader.pages)


def preview(text, limit):
    text = text.strip()
    if limit and len(text) > limit:
        return text[:limit].rstrip() + f"\n... ({len(text) - limit} more characters)"
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract text from PDFs.")
    parser.add_argument("files", nargs="+", type=Path, help="PDF files")
    parser.add_argument("--markers", action="store_true", help="mark where each page starts")
    parser.add_argument("--preview", type=int, default=600,
                        help="characters of each file to show (0 = all; default 600)")
    parser.add_argument("-o", "--outdir", type=Path, help="folder for the .txt files")
    parser.add_argument("--apply", action="store_true",
                        help="really write the .txt files (default only prints a preview)")
    args = parser.parse_args(argv)

    status, written = 0, 0
    for path in args.files:
        try:
            text, pages = extract(path, args.markers)
        except (PyPdfError, OSError, ValueError) as err:
            print(f"{path.name}: can't read it ({err})", file=sys.stderr)
            status = 1
            continue
        words = len(text.split())
        print(f"== {path.name}: {pages} page(s), {words} word(s)")
        if not text.strip():
            print("(no text found: this PDF may be a scan of images)")
        elif args.apply:
            target = (args.outdir or path.parent) / f"{path.stem}.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text + "\n", encoding="utf-8")
            print(f"wrote {target}")
            written += 1
        else:
            print(preview(text, args.preview))
    if args.apply:
        print(f"Wrote {written} text file(s).")
    elif status == 0:
        print("\nPreview only. Use --apply to save .txt files.")
    return status


if __name__ == "__main__":
    sys.exit(main())
