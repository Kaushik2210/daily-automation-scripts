"""Merge several CSV files into one, matching columns by name."""
import argparse
import csv
import sys
from pathlib import Path


def read_dicts(path, delimiter=","):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        return list(reader.fieldnames or []), list(reader)


def merge(tables, source_names=None):
    """tables: list of (columns, rows). Returns (columns, rows) with the column union.

    If source_names is given, a 'source' column records which file each row came from.
    """
    columns = list(dict.fromkeys(c for cols, _ in tables for c in cols))
    merged = []
    for index, (_, rows) in enumerate(tables):
        for row in rows:
            record = {c: row.get(c, "") for c in columns}
            if source_names:
                record["source"] = source_names[index]
            merged.append(record)
    if source_names:
        columns.append("source")
    return columns, merged


def main(argv=None):
    parser = argparse.ArgumentParser(description="Merge CSV files with matching columns.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=Path("merged.csv"))
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--add-source", action="store_true",
                        help="add a 'source' column with each row's file name")
    parser.add_argument("--apply", action="store_true",
                        help="really write the output (default is a dry run)")
    args = parser.parse_args(argv)
    for path in args.files:
        if not path.is_file():
            parser.error(f"not a file: {path}")

    tables = [read_dicts(path, args.delimiter) for path in args.files]
    names = [p.name for p in args.files] if args.add_source else None
    columns, rows = merge(tables, names)
    for path, (cols, body) in zip(args.files, tables, strict=True):
        print(f"{path.name}: {len(body)} row(s), {len(cols)} column(s)")
    print(f"Merged: {len(rows)} row(s), {len(columns)} column(s): {', '.join(columns)}")
    if args.apply:
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, delimiter=args.delimiter)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {args.output}.")
    else:
        print(f"Dry run: would write {args.output}. Use --apply to do it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
