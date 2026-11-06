"""Count the pages in PDF files and folders of PDFs."""
import argparse
import sys
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError


def find_pdfs(paths, recursive=False):
    files = []
    for path in paths:
        if path.is_dir():
            pattern = "**/*" if recursive else "*"
            files.extend(sorted(p for p in path.glob(pattern)
                                if p.is_file() and p.suffix.lower() == ".pdf"))
        else:
            files.append(path)
    return files


def count_pages(path):
    """Return the page count, or raise ValueError with a short reason."""
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise ValueError("password protected")
        return len(reader.pages)
    except (PyPdfError, OSError) as err:
        raise ValueError(f"not a readable PDF ({err})") from err


def human_size(num):
    size = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def main(argv=None):
    parser = argparse.ArgumentParser(description="Count pages across PDFs.")
    parser.add_argument("paths", nargs="+", type=Path, help="PDF files or folders")
    parser.add_argument("-r", "--recursive", action="store_true", help="look in subfolders too")
    args = parser.parse_args(argv)

    total, good, bad = 0, 0, 0
    files = find_pdfs(args.paths, args.recursive)
    width = max((len(p.name) for p in files), default=4)
    for path in files:
        try:
            pages = count_pages(path)
        except (ValueError, OSError) as err:
            print(f"{path.name:<{width}}  skipped: {err}")
            bad += 1
            continue
        print(f"{path.name:<{width}}  {pages:>5} page(s)  {human_size(path.stat().st_size):>9}")
        total += pages
        good += 1
    print(f"{good} PDF(s), {total} page(s) in total" + (f", {bad} skipped." if bad else "."))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
