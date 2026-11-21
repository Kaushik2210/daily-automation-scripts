# sqlite-csv-importer

## Purpose
Turn CSV files into SQL tables you can query. Each CSV becomes a table in a SQLite database (a single portable file): column names are cleaned into safe SQL names, the type of each column (INTEGER, REAL or TEXT) is worked out from the data, empty cells and markers like `NA` become real NULLs, and values with leading zeros (zip codes, phone numbers, ids) are kept as text so the zeros aren't lost.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python sqlite_csv_importer.py a.csv [b.csv ...] --db mydata.db [--table NAME] [--if-exists fail|replace|append] [--apply]
```
**Dry run by default:** it shows each table, its columns and types and the row count, without touching the database. Add `--apply` to write. The table is named after the file unless you pass `--table` (single file only). If a table already exists the import stops (`fail`), unless you choose `replace` (drop and recreate) or `append` (only when the columns match). Then query the result with `sqlite-query-cli`.

## Example
```bash
python sqlite_csv_importer.py customers.csv orders.csv --db demo.db --apply
```
```
{{OUTPUT}}
```

## Notes
- Dates stay as text in ISO form (`2024-03-12`), which SQLite can sort and compare correctly.
- Rows shorter than the header are padded with NULLs; a header-only file creates an empty table.
- The database file is created if needed; existing tables you don't mention are left alone.
