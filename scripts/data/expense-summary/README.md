# expense-summary

## Purpose
Summarise one month of spending from a CSV: totals by category with each category's share,
the change since the month before, the biggest single expenses, a daily average and budget checks.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python expense_summary.py expenses.csv
python expense_summary.py expenses.csv --month 2026-10 --top 5
python expense_summary.py expenses.csv --budget groceries=400 --budget "eating out=120"
python expense_summary.py expenses.csv --format markdown
```

The CSV needs `date` (YYYY-MM-DD), `amount` and `category` columns; `note` is optional. It is the
same layout `expense-logger` writes. Without `--month` the latest month in the file is used.

- Amounts use exact decimal arithmetic, and `1,020.10` style numbers are understood.
- Rows that can't be read are skipped and listed on stderr, so one typo doesn't stop the report.
- Rows with no category are grouped as `uncategorised`.
- Formats: `text` (default), `markdown`, `json`.

## Example
`expenses-2026.csv --budget groceries=400 --budget dining=150`

```
Expenses for 2026-11 (27 entries)

Category       Amount  Share  vs 2026-10
rent           900.00    46%       +0.00
utilities      501.26    25%     +389.43
dining         186.71     9%      +29.27
transport      129.68     7%      -62.08
fun            113.46     6%       -7.23
groceries       92.65     5%      -61.55
coffee          26.87     1%       +3.05
health          26.02     1%     -182.00
Total        1,976.65            +108.89

Daily average: 65.89
Biggest expenses:
  2026-11-01     900.00  rent - monthly rent
  2026-11-19     110.94  utilities - utilities spend
  2026-11-28     102.68  utilities - utilities spend
Budgets:
  groceries: 92.65 of 400.00 (307.35 left)
  dining: 186.71 of 150.00 (OVER by 36.71)
```

## Notes
- The change column compares with the previous calendar month, if the file has it.
- The daily average divides by the number of days in the month.
