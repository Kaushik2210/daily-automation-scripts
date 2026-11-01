# csv-splitter

## Purpose
Break a huge CSV into smaller files that open in a spreadsheet or fit an upload limit. Every part gets the original header row.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python csv_splitter.py FILE [--rows N] [-o OUTDIR] [--delimiter CHAR] [--apply]
```
Dry run by default: it lists the parts it would create. Pass `--apply` to write them.

## Example
```bash
python csv_splitter.py orders.csv --rows 50000 -o parts --apply
```
```
parts/orders_part001.csv  (50000 rows)
parts/orders_part002.csv  (50000 rows)
parts/orders_part003.csv  (12874 rows)
Wrote 3 part(s).
```

## Notes
- The file is streamed, so memory use stays small however large it is.
- The original file is never changed.
- Parts are named `<name>_part001.csv`, `<name>_part002.csv` and so on.
