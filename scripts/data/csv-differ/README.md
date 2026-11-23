# csv-differ

## Purpose
See exactly what changed between two versions of a CSV file. You choose the column(s) that identify a row (an id, an email, or a combination) and the tool reports the rows that were **added**, the rows that were **removed**, and the rows that were **changed**, with the old and new value of every field that differs. It also notes columns that appeared or disappeared. Handy for comparing exports from two dates, checking a data cleanup, or reviewing a pipeline's output.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python csv_differ.py old.csv new.csv [--key id] [--ignore updated_at,score] [--loose] [--max 20] [--format text|csv]
```
`--key` takes one or more column names separated by commas (default: the first column); it must be unique in both files, otherwise the tool says so and stops. `--ignore` leaves columns out of the comparison. `--loose` treats `66` and `66.0`, `Yes` and `yes`, and extra spaces as equal. `--format csv` prints a machine-readable list (`change,key,column,old,new`) instead of the report. The exit code is 0 when the files match, 1 when they differ and 2 on problems such as a duplicate key.

## Example
```bash
python csv_differ.py customers-v1.csv customers-v2.csv --key id
```
```
customers-v1.csv (6 rows) -> customers-v2.csv (6 rows), key: id

Added (1):
  + 16  name=Omar Haddad, email=omar.haddad@example.com, status=active, score=70.0

Removed (1):
  - 5  name=Emma Wilson, email=emma.wilson@example.com, status=active, score=79.5

Changed (2):
  ~ 1
      email: 'asha.rao@example.com' -> 'asha.rao@newmail.example'
  ~ 3
      status: 'inactive' -> 'active'
      score: '65.5' -> '66.0'

1 added, 1 removed, 2 changed.
```

## Notes
- Row order doesn't matter; only the key decides which rows belong together.
- Large lists are cut at `--max` entries per section; use `--format csv` to get everything.
- Use `data-profiler` to understand one file and `csv-schema-validator` to check it against rules.
