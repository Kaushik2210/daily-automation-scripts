"""Rename invoice PDFs to 'date_vendor_number.pdf' using the text inside them."""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

MONTHS = ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y")
NUMBER_RE = re.compile(r"invoice\s*(?:no\.?|number|num|#)\s*[:#]?\s*([A-Z0-9][A-Z0-9/_-]*)",
                       re.IGNORECASE)
DATE_RES = [re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),
            re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b"),
            re.compile(r"\b([A-Za-z]{3,9}\.? \d{1,2}, \d{4}|\d{1,2} [A-Za-z]{3,9}\.? \d{4})\b")]


def find_date(text, dayfirst=True):
    """Return the first date in the text as YYYY-MM-DD, or None."""
    iso = DATE_RES[0].search(text)
    if iso:
        return f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"
    slash = DATE_RES[1].search(text)
    if slash:
        a, b, year = (int(x) for x in slash.groups())
        day, month = (a, b) if dayfirst else (b, a)
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None
    words = DATE_RES[2].search(text)
    if words:
        for fmt in MONTHS:
            try:
                return datetime.strptime(words.group(1).replace(".", ""), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


def parse_invoice(text, dayfirst=True):
    """Return {'date', 'vendor', 'number'}; missing parts are None."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    number = NUMBER_RE.search(text)
    return {"date": find_date(text, dayfirst), "vendor": lines[0] if lines else None,
            "number": number.group(1) if number else None}


def safe(text):
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")


def new_name(info, pattern="{date}_{vendor}_{number}"):
    """Build the file name, or None if the invoice is missing a part the pattern needs."""
    if any(f"{{{key}}}" in pattern and not info.get(key) for key in ("date", "vendor", "number")):
        return None
    values = {key: safe(info[key]) if info.get(key) else "" for key in ("date", "vendor", "number")}
    return pattern.format(**values) + ".pdf"


def read_text(path):
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise ValueError("password protected")
    return "\n".join((page.extract_text() or "") for page in reader.pages[:2])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rename invoice PDFs from their contents.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--pattern", default="{date}_{vendor}_{number}",
                        help="name pattern using {date}, {vendor} and {number}")
    parser.add_argument("--monthfirst", action="store_true",
                        help="read 03/04/2026 as March 4 (default: 3 April)")
    parser.add_argument("--apply", action="store_true",
                        help="really rename the files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    renamed = skipped = 0
    taken = set()
    for path in sorted(args.folder.glob("*.pdf")):
        try:
            info = parse_invoice(read_text(path), dayfirst=not args.monthfirst)
        except (PyPdfError, OSError, ValueError) as err:
            print(f"skip {path.name}: can't read it ({err})")
            skipped += 1
            continue
        name = new_name(info, args.pattern)
        if not name:
            found = ", ".join(f"{k}={v}" for k, v in info.items() if v) or "nothing"
            print(f"skip {path.name}: couldn't find everything the pattern needs (found {found})")
            skipped += 1
        elif name == path.name:
            continue
        elif (path.with_name(name)).exists() or name in taken:
            print(f"skip {path.name}: {name} already exists")
            skipped += 1
        else:
            print(f"{path.name} -> {name}")
            taken.add(name)
            if args.apply:
                path.rename(path.with_name(name))
            renamed += 1
    verb = "Renamed" if args.apply else "Would rename"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {renamed} invoice(s), skipped {skipped}.{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
