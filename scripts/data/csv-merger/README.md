# csv-merger

## Purpose
Combine several CSV files (monthly exports, per-region sheets) into a single file. Columns are matched by name, so files don't need identical column order, and missing values are left blank.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python csv_merger.py FILE FILE [FILE ...] [-o OUTPUT] [--add-source] [--apply]
```
Dry run by default: it reports what the merged file would contain. Pass `--apply` to write it (default output `merged.csv`). `--add-source` adds a `source` column with each row's file name.

## Example
```bash
python csv_merger.py jan.csv feb.csv mar.csv -o q1.csv --add-source --apply
```
```
jan.csv: 120 row(s), 4 column(s)
feb.csv: 98 row(s), 4 column(s)
mar.csv: 131 row(s), 5 column(s)
Merged: 349 row(s), 6 column(s): date, region, amount, notes, channel, source
Wrote q1.csv.
```

## Notes
- The input files are never modified.
- All files must use the same delimiter (set it with `--delimiter`).
