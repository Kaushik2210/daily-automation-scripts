"""Convert a CSV file into JSON records (or JSON Lines)."""
import argparse
import csv
import json
import sys
from pathlib import Path


def convert_value(text):
    """Turn '12' into 12, '3.5' into 3.5, 'true' into True and '' into None."""
    value = text.strip()
    if value == "":
        return None
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            continue
    return text


def rows_to_records(rows, infer_types=False):
    """First row is the header; returns a list of dicts."""
    if not rows:
        return []
    header = rows[0]
    records = []
    for row in rows[1:]:
        padded = row + [""] * (len(header) - len(row))
        values = [convert_value(v) if infer_types else v for v in padded[:len(header)]]
        records.append(dict(zip(header, values, strict=True)))
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert CSV to JSON.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--types", action="store_true",
                        help="detect numbers, booleans and empty values")
    parser.add_argument("--lines", action="store_true", help="one JSON object per line")
    parser.add_argument("-o", "--output", type=Path, help="write the result to this file")
    parser.add_argument("--apply", action="store_true",
                        help="really write --output (default only prints the result)")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")

    with args.file.open(newline="", encoding="utf-8-sig") as handle:
        records = rows_to_records(list(csv.reader(handle, delimiter=args.delimiter)), args.types)
    if args.lines:
        result = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
    else:
        result = json.dumps(records, indent=2, ensure_ascii=False)
    if args.output and args.apply:
        args.output.write_text(result + "\n", encoding="utf-8")
        print(f"Wrote {len(records)} record(s) to {args.output}.")
    else:
        print(result)
        if args.output:
            print(f"(preview only: use --apply to write {args.output})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
