# csv-column-stats

## Purpose
Get a fast overview of a CSV file before you work with it. For each column you see how many values are filled or blank and how many are unique, plus min, max, mean and median for numbers or the most common values for text.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python csv_column_stats.py FILE [--delimiter CHAR]
```

## Example
```bash
python csv_column_stats.py sales.csv
```
```
120 data row(s), 3 column(s)

region  [text]  filled=120 blank=0 unique=4
    top: north (41), south (38), east (27)
amount  [number]  filled=118 blank=2 unique=97
    min=4.5 max=980 mean=212.33 median=180
```

## Notes
- A column counts as numeric only if every filled value is a number (thousands commas are fine).
- Read-only.
