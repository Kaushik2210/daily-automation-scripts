"""Tidy a CSV file: trim cells, drop blank rows and normalize the header names."""
import argparse
import csv
import re
import sys
from pathlib import Path


def clean_header(name):
    """'  First Name! ' -> 'first_name'."""
    return re.sub(r"[^0-9a-z]+", "_", name.strip().lower()).strip("_") or "column"


def unique(names):
    seen, result = {}, []
    for name in names:
        seen[name] = seen.get(name, 0) + 1
        result.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
    return result


def clean_rows(rows, normalize_headers=True):
    """Return (cleaned_rows, stats). The first row is the header."""
    stats = {"blank_rows": 0, "trimmed_cells": 0, "padded_rows": 0}
    if not rows:
        return [], stats
    width = max(len(r) for r in rows)
    cleaned = []
    for row in rows:
        stripped = [cell.strip() for cell in row]
        stats["trimmed_cells"] += sum(a != b for a, b in zip(row, stripped, strict=True))
        if not any(stripped):
            stats["blank_rows"] += 1
            continue
        if len(stripped) < width:
            stats["padded_rows"] += 1
            stripped += [""] * (width - len(stripped))
        cleaned.append(stripped)
    if cleaned and normalize_headers:
        cleaned[0] = unique([clean_header(h) for h in cleaned[0]])
    return cleaned, stats


def detect_delimiter(sample):
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def main(argv=None):
    parser = argparse.ArgumentParser(description="Clean up a CSV file.")
    parser.add_argument("file", type=Path)
    parser.add_argument("-o", "--output", type=Path, help="write here (default: overwrite input)")
    parser.add_argument("--keep-headers", action="store_true", help="don't rename the headers")
    parser.add_argument("--apply", action="store_true",
                        help="really write the file (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")

    text = args.file.read_text(encoding="utf-8-sig")
    delimiter = detect_delimiter(text[:4096])
    rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
    cleaned, stats = clean_rows(rows, not args.keep_headers)
    print(f"{len(rows)} row(s) in, {len(cleaned)} out: {stats['blank_rows']} blank removed, "
          f"{stats['trimmed_cells']} cell(s) trimmed, {stats['padded_rows']} short row(s) padded.")
    if cleaned:
        print("Header:", delimiter.join(cleaned[0]))
    target = args.output or args.file
    if args.apply:
        with target.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle, delimiter=delimiter).writerows(cleaned)
        print(f"Wrote {target}.")
    else:
        print(f"Dry run: would write {target}. Use --apply to do it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
