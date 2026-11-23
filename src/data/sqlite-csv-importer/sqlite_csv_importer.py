"""Load one or more CSV files into tables of a SQLite database."""
import argparse
import csv
import re
import sqlite3
import sys
from pathlib import Path

NULLS = {"", "na", "n/a", "null", "none", "nan"}


def clean_name(name, used=()):
    """A safe SQL identifier: lowercase letters, digits and underscores, never repeated."""
    text = re.sub(r"[^0-9a-z]+", "_", name.strip().lower()).strip("_") or "column"
    if text[0].isdigit():
        text = "_" + text
    candidate, number = text, 2
    while candidate in used:
        candidate, number = f"{text}_{number}", number + 1
    return candidate


def column_type(values):
    """INTEGER, REAL or TEXT, from the non-empty values of a column."""
    values = [v.strip() for v in values if v.strip().lower() not in NULLS]
    if any(re.fullmatch(r"[-+]?0\d+", v) for v in values):
        return "TEXT"  # zip codes, phone numbers and ids with leading zeros must stay as text
    if values and all(re.fullmatch(r"[-+]?\d+", v) for v in values):
        return "INTEGER"
    if values and all(_float(v) for v in values):
        return "REAL"
    return "TEXT"


def _float(text):
    try:
        float(text)
    except ValueError:
        return False
    return not text.strip().lower().lstrip("+-").startswith(("inf", "nan"))


def convert(value, kind):
    value = value.strip()
    if value.lower() in NULLS:
        return None
    if kind == "INTEGER":
        return int(value)
    if kind == "REAL":
        return float(value)
    return value


def plan_table(path, delimiter):
    """Read the CSV and return (names, original headers, types, rows)."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        header = next(reader, [])
        rows = [r + [""] * (len(header) - len(r)) for r in reader if r]
    names = []
    for original in header:
        names.append(clean_name(original, names))
    kinds = [column_type([r[i] for r in rows]) for i in range(len(header))]
    return names, header, kinds, rows


def table_exists(con, table):
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                       (table,)).fetchone() is not None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Load CSV files into a SQLite database.")
    parser.add_argument("csv", nargs="+", type=Path, help="CSV files to import")
    parser.add_argument("--db", type=Path, required=True, help="SQLite database file")
    parser.add_argument("--table", help="table name (only with a single CSV; default: file name)")
    parser.add_argument("--if-exists", choices=["fail", "replace", "append"], default="fail",
                        help="what to do when the table already exists (fail)")
    parser.add_argument("--delimiter", default=",", help="field separator (,)")
    parser.add_argument("--apply", action="store_true",
                        help="really write to the database (default is a dry run)")
    args = parser.parse_args(argv)
    if args.table and len(args.csv) > 1:
        parser.error("--table can only be used with a single CSV file")
    for path in args.csv:
        if not path.is_file():
            parser.error(f"not a file: {path}")

    con = sqlite3.connect(args.db if args.apply or args.db.exists() else ":memory:")
    problems = 0
    try:
        for path in args.csv:
            table = clean_name(args.table or path.stem)
            names, header, kinds, rows = plan_table(path, args.delimiter)
            if not header:
                print(f"{path.name}: empty file, skipped")
                problems += 1
                continue
            exists = table_exists(con, table)
            action = "create"
            if exists:
                if args.if_exists == "fail":
                    print(f"{path.name}: table '{table}' already exists "
                          "(use --if-exists replace or append)")
                    problems += 1
                    continue
                action = args.if_exists
            print(f"{path.name} -> table {table} ({action}): {len(rows)} row(s)")
            for name, original, kind in zip(names, header, kinds, strict=True):
                note = f"  (from '{original}')" if name != original else ""
                print(f"    {name:<20} {kind}{note}")
            if not args.apply:
                continue
            if exists and action == "replace":
                con.execute(f'DROP TABLE "{table}"')
            if not exists or action == "replace":
                columns = ", ".join(f'"{n}" {k}' for n, k in zip(names, kinds, strict=True))
                con.execute(f'CREATE TABLE "{table}" ({columns})')
            elif [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')] != names:
                print("    the existing table has different columns; nothing imported")
                problems += 1
                continue
            marks = ", ".join("?" for _ in names)
            con.executemany(f'INSERT INTO "{table}" VALUES ({marks})',
                            [[convert(v, k) for v, k in zip(r, kinds, strict=True)] for r in rows])
            con.commit()
            total = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            print(f"    done: table '{table}' now has {total} row(s)")
    except (sqlite3.Error, ValueError) as err:
        print(f"Import failed: {err}", file=sys.stderr)
        con.rollback()
        return 1
    finally:
        con.close()
    if not args.apply:
        print(f"\nDry run. Use --apply to write {args.db}.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
