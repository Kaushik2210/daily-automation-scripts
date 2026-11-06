"""Split a big CSV file into smaller parts, repeating the header in each."""
import argparse
import csv
import sys
from pathlib import Path


def chunks(rows, size):
    """Yield lists of at most `size` rows."""
    chunk = []
    for row in rows:
        chunk.append(row)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def part_name(stem, number, width=3):
    return f"{stem}_part{number:0{width}d}.csv"


def split_file(source, size, outdir, apply=False, delimiter=","):
    """Return a list of (path, row_count). Files are only written when apply is True."""
    results = []
    with source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        header = next(reader, None)
        if header is None:
            return results
        for number, chunk in enumerate(chunks(reader, size), 1):
            target = outdir / part_name(source.stem, number)
            if apply:
                with target.open("w", newline="", encoding="utf-8") as out:
                    writer = csv.writer(out, delimiter=delimiter)
                    writer.writerow(header)
                    writer.writerows(chunk)
            results.append((target, len(chunk)))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Split a CSV file into parts.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--rows", type=int, default=1000, help="data rows per part (default 1000)")
    parser.add_argument("-o", "--outdir", type=Path, help="folder for the parts (default: same)")
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--apply", action="store_true",
                        help="really write the parts (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")
    if args.rows < 1:
        parser.error("--rows must be at least 1")

    outdir = args.outdir or args.file.parent
    if args.apply:
        outdir.mkdir(parents=True, exist_ok=True)
    parts = split_file(args.file, args.rows, outdir, args.apply, args.delimiter)
    for path, count in parts:
        print(f"{path}  ({count} rows)")
    verb = "Wrote" if args.apply else "Would write"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {len(parts)} part(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
