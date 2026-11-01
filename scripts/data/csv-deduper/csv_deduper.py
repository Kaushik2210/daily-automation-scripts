"""Remove duplicate rows from a CSV, comparing all columns or just the ones you pick."""
import argparse
import csv
import sys
from pathlib import Path


def dedupe(rows, columns=None, keep="first", ignore_case=False):
    """rows[0] is the header. Returns (kept_rows, removed_count)."""
    if not rows:
        return [], 0
    header, body = rows[0], rows[1:]
    indexes = [header.index(c) for c in columns] if columns else list(range(len(header)))

    def key(row):
        parts = [row[i].strip() if i < len(row) else "" for i in indexes]
        return tuple(p.lower() for p in parts) if ignore_case else tuple(parts)

    ordered = body if keep == "first" else list(reversed(body))
    seen, kept = set(), []
    for row in ordered:
        k = key(row)
        if k not in seen:
            seen.add(k)
            kept.append(row)
    if keep == "last":
        kept.reverse()
    return [header, *kept], len(body) - len(kept)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Remove duplicate rows from a CSV file.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--columns", help="comma-separated columns that define a duplicate")
    parser.add_argument("--keep", choices=["first", "last"], default="first")
    parser.add_argument("-i", "--ignore-case", action="store_true")
    parser.add_argument("-o", "--output", type=Path, help="write here (default: overwrite input)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the file (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")

    with args.file.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    columns = [c.strip() for c in args.columns.split(",")] if args.columns else None
    if columns and rows:
        missing = [c for c in columns if c not in rows[0]]
        if missing:
            parser.error(f"unknown column(s): {', '.join(missing)}")
    kept, removed = dedupe(rows, columns, args.keep, args.ignore_case)
    total, left = max(len(rows) - 1, 0), max(len(kept) - 1, 0)
    print(f"{total} data row(s), {removed} duplicate(s), {left} kept.")
    target = args.output or args.file
    if args.apply:
        with target.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerows(kept)
        print(f"Wrote {target}.")
    else:
        print(f"Dry run: would write {target}. Use --apply to do it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
