# csv-deduper

## Purpose
Remove repeated rows from a CSV. By default a row is a duplicate only if every column matches; with `--columns` you choose which columns define a duplicate, for example just `email`.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python csv_deduper.py FILE [--columns a,b] [--keep first|last] [-i] [-o OUTPUT] [--apply]
```
Dry run by default: it reports how many duplicates it found. Pass `--apply` to write the result, to `-o` or over the input.

## Example
```bash
python csv_deduper.py contacts.csv --columns email -i -o unique.csv --apply
```
```
2400 data row(s), 187 duplicate(s), 2213 kept.
Wrote unique.csv.
```

## Notes
- Surrounding spaces are ignored when comparing values.
- `--keep last` keeps the most recent occurrence, which suits exports sorted oldest first.
- Row order is preserved.
