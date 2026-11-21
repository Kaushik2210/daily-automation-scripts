# data-anonymizer

## Purpose
Share a dataset without sharing people's details. The tool finds the personal columns of a CSV (emails, names, phone numbers, IP addresses, card numbers, national ids) from their headers and values, and masks them: emails become `user_6de6d529@example.com`, names become made-up names, phone numbers keep only their last two digits, cards keep the last four. The same input always gives the same output (for a given `--salt`), so rows about the same person still match and joins keep working.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python data_anonymizer.py data.csv [--mask COLUMN:KIND] [--keep COLUMN] [--no-auto] [--salt SECRET] [-o OUT.csv] [--apply]
```
Kinds: `email`, `name`, `phone`, `card`, `ip`, `hash`, `redact`, `year` (keeps only the year of a date) and `scrub` (replaces emails and phone numbers found inside free text). **Dry run by default:** it lists the detected columns and previews the first rows. With `--apply` it writes `NAME.anonymized.csv` (or `-o`) and never overwrites an existing file. Use `--mask` to name columns the tool missed, `--keep` for ones it shouldn't touch and `--no-auto` to mask only what you name.

## Example
```bash
python data_anonymizer.py customers.csv
```
```
{{OUTPUT}}
```

## Notes
- This is **pseudonymisation**, not a guarantee of anonymity: other columns (age, country, dates) can still identify someone when combined. Review the result before sharing.
- Keep your `--salt` secret; anyone who knows it can test guesses against the masked values.
- Empty cells stay empty, and the original file is never modified.
