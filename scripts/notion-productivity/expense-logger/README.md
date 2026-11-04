# expense-logger

## Purpose
Know where the money goes. Log each purchase in a second, then see totals per category for any month. Everything is stored in a plain CSV file that opens in a spreadsheet.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python expense_logger.py add AMOUNT CATEGORY [NOTE ...] [--date YYYY-MM-DD]
python expense_logger.py list [--month YYYY-MM]
python expense_logger.py summary [--month YYYY-MM]
```
The default file is `~/expenses.csv` (change it with `--file`). This file is the tool's own storage, so `add` writes to it straight away.

## Example
```bash
python expense_logger.py summary --month 2026-01 --file expenses.csv
```
```
groceries       100.85  #################
transport        12.00  ##
coffee            4.50  #
total           117.35  (4 expenses)
```

## Notes
- Amounts use exact decimal arithmetic, so 0.10 + 0.20 is exactly 0.30.
- Currency symbols and thousands commas in the amount are accepted and ignored.
- Categories are lowercased so `Coffee` and `coffee` are the same.
