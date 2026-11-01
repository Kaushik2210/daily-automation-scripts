# csv-cleaner

## Purpose
Fix the usual CSV annoyances in one pass: stray spaces around values, completely blank rows, short rows, and headers like `  First Name! ` that are awkward to work with.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python csv_cleaner.py FILE [-o OUTPUT] [--keep-headers] [--apply]
```
Dry run by default: it prints what it would change. Pass `--apply` to write the result to `-o`, or over the input file if you give no `-o`.

## Example
```bash
python csv_cleaner.py contacts.csv -o contacts_clean.csv --apply
```
```
5 row(s) in, 3 out: 2 blank removed, 4 cell(s) trimmed, 1 short row(s) padded.
Header: first_name,last_name,age
Wrote contacts_clean.csv.
```

## Notes
- The delimiter (comma, semicolon, tab or pipe) is detected and kept.
- Headers become lowercase `snake_case`; repeated names get `_2`, `_3`.
- Use `-o` while you're unsure, so the original file stays untouched.
