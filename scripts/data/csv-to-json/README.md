# csv-to-json

## Purpose
Turn a CSV file into JSON that code or APIs can use: a list of objects keyed by the header names, or JSON Lines with one object per line.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python csv_to_json.py FILE [--types] [--lines] [--delimiter CHAR] [-o OUTPUT --apply]
```
Everything stays text unless you pass `--types`, which converts numbers and `true`/`false` and turns empty cells into `null`. The result is printed unless you pass `-o` with `--apply`.

## Example
```bash
python csv_to_json.py people.csv --types
```
```
[
  {
    "name": "Ada",
    "age": 36
  },
  {
    "name": "Lin",
    "age": null
  }
]
```

## Notes
- Short rows are padded with empty values; extra cells beyond the header are dropped.
- A UTF-8 byte-order mark at the start of the file is handled.
