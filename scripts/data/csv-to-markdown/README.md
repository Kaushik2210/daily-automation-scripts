# csv-to-markdown

## Purpose
Turn a CSV file into a markdown table you can paste into a README, issue or note.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python csv_to_markdown.py FILE [--delimiter CHAR] [--align left|right|center]
```

## Example
```bash
python csv_to_markdown.py scores.csv --align right
```
```
| name | score |
| ---: | ---: |
| ada | 10 |
| lin | 7 |
```

## Notes
- The first row is used as the header.
- Pipes inside cells are escaped and line breaks are turned into spaces.
- Rows shorter than the header are padded with empty cells.
