# json-to-csv

## Purpose
Open JSON data in a spreadsheet. Takes a list of JSON objects (for example an API response) and writes one CSV row per object, flattening nested objects into dotted column names.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python json_to_csv.py FILE [--key PATH] [-o OUTPUT --apply]
```
If the file is an object holding one list of records (like `{"items": [...]}`) it is found automatically. Otherwise give the list's path with `--key`, for example `--key data.items`. The CSV is printed unless you pass `-o` with `--apply`.

## Example
```bash
python json_to_csv.py users.json
```
```
id,name,address.city
1,Ada,London
2,Lin,Shanghai
```

## Notes
- Columns are the union of every key, in the order they first appear; missing values are blank.
- Lists inside a record are written as JSON text in a single cell.
- Anything that isn't a list of objects stops with an error and exit code 1.
