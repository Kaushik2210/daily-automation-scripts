# csv-schema-validator

## Purpose
Catch bad data before it reaches your database or report. You describe what each column should look like in a small JSON schema (type, required, unique, minimum/maximum, allowed values, a pattern, a date format) and the tool checks every row, listing the exact line, column, value and reason for each problem. If you don't have a schema yet, `--infer` writes a first draft from the data itself.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python csv_schema_validator.py data.csv schema.json [--max-errors 20]
python csv_schema_validator.py data.csv --infer > schema.json
```
A schema looks like this:
```json
{"strict": true,
 "columns": {
   "id":     {"type": "int", "required": true, "unique": true, "min": 1},
   "email":  {"type": "str", "pattern": "^[^@\s]+@[^@\s]+$"},
   "status": {"type": "str", "allowed": ["active", "inactive"]},
   "joined": {"type": "date", "format": "%Y-%m-%d"}}}
```
Types are `str`, `int`, `float`, `bool`, `date` and `datetime`. Other rules: `required`, `unique`, `min`, `max`, `min_length`, `max_length`, `allowed`, `pattern`. Empty cells are fine unless the column is `required`. With `"strict": true`, columns that aren't in the schema are reported too. The exit code is 1 if anything is wrong, so it can gate a pipeline.

## Example
```bash
python csv_schema_validator.py customers.csv customers-schema.json
```
```
line 9    id           '7' is a duplicate (first seen on line 8)
line 11   email        'not-an-email' does not match the pattern ^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$
line 12   name         is required but empty
line 13   age          '150' is above the maximum of 120
line 14   status       'pending' is not one of active, inactive
line 15   signup_date  '12/31/2024' is not a valid date (expected format %Y-%m-%d)
line 16   score        'n/a' is not a valid float

16 row(s) checked: 7 problem(s) on 7 row(s) - id (1), email (1), name (1), age (1), status (1), signup_date (1), score (1), 0 structure problem(s).
```

## Notes
- Line numbers are lines of the file (the header is line 1).
- `--infer` is only a guess: review it, then tighten it by hand (for example add `allowed` lists or a `pattern`).
- Use `data-profiler` to understand a dataset first, and `json-schema-validator` for JSON documents.
