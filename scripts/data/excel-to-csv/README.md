# excel-to-csv

## Purpose
Turn an Excel workbook into plain CSV files, one per sheet, so the data can go into scripts, databases or version control.

## Install
Needs openpyxl:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python excel_to_csv.py FILE.xlsx [--sheet NAME] [-o OUTDIR] [--apply]
```
Dry run by default: it lists the files it would create. Pass `--apply` to write them. Files are named `<workbook>_<sheet>.csv`.

## Example
```bash
python excel_to_csv.py budget.xlsx -o csv --apply
```
```
Income: 14 row(s) -> csv/budget_Income.csv
Expenses: 52 row(s) -> csv/budget_Expenses.csv
Wrote 2 file(s).
```

## Notes
- Formulas are exported as their last calculated values (as Excel saved them).
- Dates become ISO text (`2026-01-05`, with the time only when there is one) and whole numbers lose the trailing `.0`.
- Only the modern `.xlsx` format is supported, not the old `.xls`.
