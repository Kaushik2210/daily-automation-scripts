"""Show which rows were added, removed or changed between two CSV files."""
import argparse
import csv
import io
import sys
from pathlib import Path


def read(path, delimiter=","):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        header = [h.strip() for h in next(reader, [])]
        rows = [r + [""] * (len(header) - len(r)) for r in reader if r]
    return header, rows


def index_rows(header, rows, keys):
    """Return ({key tuple: row dict}, [duplicate keys])."""
    table, duplicates = {}, []
    for row in rows:
        record = dict(zip(header, row, strict=False))
        key = tuple(record[k] for k in keys)
        if key in table:
            duplicates.append(key)
        else:
            table[key] = record
    return table, duplicates


def same(a, b, loose):
    if a == b:
        return True
    if not loose:
        return False
    a, b = a.strip(), b.strip()
    if a.lower() == b.lower():
        return True
    try:
        return float(a) == float(b)
    except ValueError:
        return False


def diff(old, new, keys, ignore, loose):
    """Compare two {key: row} tables. Return (added, removed, changed)."""
    columns = [c for c in new[next(iter(new))] if c not in keys and c not in ignore] if new else []
    common = [c for c in columns if not old or c in old[next(iter(old))]]
    added = [k for k in new if k not in old]
    removed = [k for k in old if k not in new]
    changed = []
    for key in new:
        if key in old:
            fields = [(c, old[key].get(c, ""), new[key].get(c, "")) for c in common
                      if not same(old[key].get(c, ""), new[key].get(c, ""), loose)]
            if fields:
                changed.append((key, fields))
    return added, removed, changed


def label(key):
    return ", ".join(key)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare two CSV files row by row.")
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--key", help="column(s) that identify a row, comma-separated "
                                      "(default: the first column)")
    parser.add_argument("--ignore", default="", help="columns to leave out, comma-separated")
    parser.add_argument("--loose", action="store_true",
                        help="treat 66 and 66.0, 'Yes' and 'yes' and extra spaces as equal")
    parser.add_argument("--max", type=int, default=20, help="rows to list per section (20)")
    parser.add_argument("--format", choices=["text", "csv"], default="text")
    parser.add_argument("--delimiter", default=",", help="field separator (,)")
    args = parser.parse_args(argv)
    for path in (args.old, args.new):
        if not path.is_file():
            parser.error(f"not a file: {path}")

    old_header, old_rows = read(args.old, args.delimiter)
    new_header, new_rows = read(args.new, args.delimiter)
    if not old_header or not new_header:
        print("One of the files is empty.", file=sys.stderr)
        return 2
    keys = [k.strip() for k in args.key.split(",")] if args.key else [new_header[0]]
    missing = [k for k in keys if k not in old_header or k not in new_header]
    if missing:
        parser.error(f"key column(s) not in both files: {', '.join(missing)}")
    ignore = {c.strip() for c in args.ignore.split(",") if c.strip()}

    old, dup_old = index_rows(old_header, old_rows, keys)
    new, dup_new = index_rows(new_header, new_rows, keys)
    if dup_old or dup_new:
        print(f"The key {', '.join(keys)} is not unique (e.g. {label((dup_old + dup_new)[0])}); "
              "choose a different --key.", file=sys.stderr)
        return 2
    added, removed, changed = diff(old, new, keys, ignore, args.loose)
    columns_added = [c for c in new_header if c not in old_header and c not in ignore]
    columns_removed = [c for c in old_header if c not in new_header and c not in ignore]

    if args.format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["change", "key", "column", "old", "new"])
        writer.writerows(["added", label(k), "", "", ""] for k in added)
        writer.writerows(["removed", label(k), "", "", ""] for k in removed)
        for key, fields in changed:
            writer.writerows(["changed", label(key), c, o, n] for c, o, n in fields)
        print(buffer.getvalue(), end="")
    else:
        print(f"{args.old.name} ({len(old)} rows) -> {args.new.name} ({len(new)} rows), "
              f"key: {', '.join(keys)}")
        if columns_added or columns_removed:
            print(f"Columns: +{', '.join(columns_added) or '-'}  "
                  f"-{', '.join(columns_removed) or '-'}")
        sections = (("Added", added, "+", new), ("Removed", removed, "-", old))
        for title, items, sign, table in sections:
            if items:
                print(f"\n{title} ({len(items)}):")
                for key in items[:args.max]:
                    rest = ", ".join(f"{c}={v}" for c, v in table[key].items() if c not in keys)
                    print(f"  {sign} {label(key)}  {rest}"[:110])
                if len(items) > args.max:
                    print(f"  ... and {len(items) - args.max} more")
        if changed:
            print(f"\nChanged ({len(changed)}):")
            for key, fields in changed[:args.max]:
                print(f"  ~ {label(key)}")
                for column, before, after in fields:
                    print(f"      {column}: {before!r} -> {after!r}")
            if len(changed) > args.max:
                print(f"  ... and {len(changed) - args.max} more")
        if not (added or removed or changed or columns_added or columns_removed):
            print("\nNo differences.")
        else:
            print(f"\n{len(added)} added, {len(removed)} removed, {len(changed)} changed.")
    return 1 if added or removed or changed or columns_added or columns_removed else 0


if __name__ == "__main__":
    sys.exit(main())
