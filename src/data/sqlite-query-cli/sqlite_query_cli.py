"""Run SQL against a SQLite file and print the result as a table, CSV, JSON or markdown."""
import argparse
import csv
import io
import json
import sqlite3
import sys
from pathlib import Path

MAX_WIDTH = 40


def connect(path, writable):
    """Open the database read-only unless writing was asked for."""
    if writable:
        return sqlite3.connect(path)
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def cell(value):
    return "NULL" if value is None else str(value)


def render_table(columns, rows):
    """Aligned text table; numbers are right-aligned and long text is shortened."""
    shown = [[cell(v) for v in row] for row in rows]
    widths = [min(MAX_WIDTH, max([len(c)] + [len(r[i]) for r in shown]))
              for i, c in enumerate(columns)]
    numeric = [bool(rows) and all(isinstance(r[i], (int, float)) for r in rows if r[i] is not None)
               for i in range(len(columns))]

    def fit(text, width, right):
        text = text if len(text) <= width else text[:width - 1] + "…"
        return text.rjust(width) if right else text.ljust(width)

    lines = [" | ".join(fit(c, w, False) for c, w in zip(columns, widths, strict=True)),
             "-+-".join("-" * w for w in widths)]
    lines += [" | ".join(fit(v, w, n) for v, w, n in zip(r, widths, numeric, strict=True))
              for r in shown]
    return "\n".join(line.rstrip() for line in lines)


def render(columns, rows, fmt):
    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)
        return buffer.getvalue().rstrip("\n")
    if fmt == "json":
        return json.dumps([dict(zip(columns, r, strict=True)) for r in rows], indent=1,
                          default=str, ensure_ascii=False)
    if fmt == "markdown":
        lines = ["| " + " | ".join(columns) + " |", "|" + " --- |" * len(columns)]
        lines += ["| " + " | ".join(cell(v).replace("|", "\\|") for v in r) + " |" for r in rows]
        return "\n".join(lines)
    return render_table(columns, rows)


def list_tables(con):
    items = con.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') "
                        "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    result = []
    for name, kind in items:
        count = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        columns = [r[1] for r in con.execute(f'PRAGMA table_info("{name}")')]
        result.append((name, kind, count, columns))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run SQL against a SQLite database.")
    parser.add_argument("db", type=Path)
    parser.add_argument("query", nargs="?", help="one SQL statement, e.g. 'SELECT * FROM users'")
    parser.add_argument("--tables", action="store_true", help="list tables and their row counts")
    parser.add_argument("--schema", action="store_true", help="show the CREATE statements")
    parser.add_argument("--format", choices=["table", "csv", "json", "markdown"], default="table")
    parser.add_argument("--limit", type=int, default=50,
                        help="rows to print in table format, 0 for all (50)")
    parser.add_argument("--write", action="store_true",
                        help="allow statements that change the database")
    parser.add_argument("--apply", action="store_true",
                        help="with --write: keep the changes (default only shows their effect)")
    args = parser.parse_args(argv)
    if not args.db.is_file():
        parser.error(f"not a file: {args.db}")
    if not (args.query or args.tables or args.schema):
        parser.error("give a query, or --tables, or --schema")

    try:
        con = connect(args.db, args.write)
    except sqlite3.Error as err:
        print(f"Can't open the database: {err}", file=sys.stderr)
        return 1
    try:
        if args.tables or args.schema:
            if args.schema:
                for (sql,) in con.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL "
                                          "AND name NOT LIKE 'sqlite_%' ORDER BY type DESC, name"):
                    print(sql + ";")
            else:
                for name, kind, count, columns in list_tables(con):
                    print(f"{name:<20} {kind:<5} {count:>7} rows  ({', '.join(columns)})")
            if not args.query:
                return 0
        cursor = con.execute(args.query)
        if cursor.description is None:  # INSERT / UPDATE / DELETE / CREATE ...
            changed = max(cursor.rowcount, 0)
            if args.apply:
                con.commit()
                print(f"Done: {changed} row(s) changed and saved.")
            else:
                con.rollback()
                print(f"Dry run: {changed} row(s) would change. Use --apply to keep the changes.")
            return 0
        columns = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
    except sqlite3.OperationalError as err:
        message = str(err)
        if "readonly" in message:
            print("This database is open read-only. To change it, use --write "
                  "(and --apply to save).", file=sys.stderr)
        else:
            print(f"SQL error: {message}", file=sys.stderr)
        return 1
    except (sqlite3.Error, sqlite3.Warning) as err:
        print(f"SQL error: {err}", file=sys.stderr)
        return 1
    finally:
        con.close()

    shown = rows[:args.limit] if args.limit and args.format == "table" else rows
    print(render(columns, shown, args.format))
    if args.format == "table":
        more = f" (showing the first {len(shown)})" if len(shown) < len(rows) else ""
        print(f"\n{len(rows)} row(s){more}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
