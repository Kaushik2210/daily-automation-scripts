# invoice-renamer

## Purpose
Turn a folder of anonymous scans such as `scan_0001.pdf` into files you can find again: `2026-01-15_ACME-Supplies-Ltd_INV-1042.pdf`. It reads the text on the first pages, finds the invoice date, the vendor (the first line) and the invoice number, and builds the name from them.

## Install
Needs `pypdf`:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python invoice_renamer.py FOLDER [--pattern "{date}_{vendor}_{number}"] [--monthfirst] [--apply]
```
Dry run by default: it shows each rename. Pass `--apply` to rename the files. Dates like `12/02/2026` are read day first (12 February); add `--monthfirst` for US style. The pattern can use any of `{date}`, `{vendor}` and `{number}`.

## Example
```bash
python invoice_renamer.py .
```
```
skip handbook.pdf: couldn't find everything the pattern needs (found vendor=Handbook chapter 1)
skip report.pdf: couldn't find everything the pattern needs (found vendor=Quarterly report)
scan_0001.pdf -> 2026-01-15_ACME-Supplies-Ltd_INV-1042.pdf
scan_0002.pdf -> 2026-02-12_Blue-Sky-Hosting_BS-7781.pdf
Would rename 2 invoice(s), skipped 2. Use --apply to do it.
```

## Notes
- Invoices where a needed part can't be found are skipped and left alone, with a note of what was found.
- It never overwrites an existing file, and two invoices that would get the same name are not both renamed.
- Scanned images with no text layer can't be read (they need OCR first).
