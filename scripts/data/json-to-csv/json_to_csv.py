"""Flatten JSON records into a CSV file."""
import argparse
import csv
import io
import json
import sys
from pathlib import Path


def flatten(record, prefix="", sep="."):
    """{'a': {'b': 1}, 'c': [1, 2]} -> {'a.b': 1, 'c': '[1, 2]'}"""
    flat = {}
    for key, value in record.items():
        name = f"{prefix}{sep}{key}" if prefix else str(key)
        if isinstance(value, dict):
            flat.update(flatten(value, name, sep))
        elif isinstance(value, list):
            flat[name] = json.dumps(value, ensure_ascii=False)
        else:
            flat[name] = value
    return flat


def find_records(data, key=None):
    """Accept a list of objects, a single object, or an object holding the list at `key`."""
    if key:
        for part in key.split("."):
            data = data[part]
    if isinstance(data, dict) and not key:
        lists = [v for v in data.values()
                 if isinstance(v, list) and v and all(isinstance(i, dict) for i in v)]
        if len(lists) == 1:  # a wrapper like {"items": [...]}
            data = lists[0]
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("expected a list of JSON objects")
    return data


def to_csv(records):
    flat = [flatten(r) for r in records]
    columns = list(dict.fromkeys(key for row in flat for key in row))
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in flat:
        writer.writerow({k: "" if v is None else v for k, v in row.items()})
    return out.getvalue(), columns


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert JSON records to CSV.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--key", help="path to the list inside the JSON, e.g. data.items")
    parser.add_argument("-o", "--output", type=Path, help="write the CSV to this file")
    parser.add_argument("--apply", action="store_true",
                        help="really write --output (default only prints the CSV)")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")

    try:
        data = json.loads(args.file.read_text(encoding="utf-8-sig"))
        text, columns = to_csv(find_records(data, args.key))
    except (json.JSONDecodeError, KeyError, ValueError) as err:
        print(f"Couldn't convert {args.file}: {err}", file=sys.stderr)
        return 1
    if args.output and args.apply:
        args.output.write_text(text, encoding="utf-8", newline="")
        print(f"Wrote {args.output} with {len(columns)} column(s).")
    else:
        print(text.rstrip("\n"))
        if args.output:
            print(f"(preview only: use --apply to write {args.output})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
