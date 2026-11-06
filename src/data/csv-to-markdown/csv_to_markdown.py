"""Convert a CSV file into a markdown table."""
import argparse
import csv
import sys
from pathlib import Path


def clean_cell(cell):
    return cell.replace("|", r"\|").replace("\n", " ")


def to_markdown(rows, align=None):
    """Return a markdown table; the first row is the header."""
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    rows = [[clean_cell(c) for c in row] + [""] * (width - len(row)) for row in rows]
    marks = {"left": ":---", "right": "---:", "center": ":---:"}.get(align, "---")
    lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join([marks] * width) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in rows[1:]]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert a CSV file to a markdown table.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--delimiter", default=",", help="field separator (default: ,)")
    parser.add_argument("--align", choices=["left", "right", "center"], help="column alignment")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")

    with args.file.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle, delimiter=args.delimiter))
    table = to_markdown(rows, args.align)
    print(table or "The CSV file is empty.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
