# pdf-metadata-viewer

## Purpose
Look inside a PDF without opening it: title, author, creating program, dates, page count, page size (recognised as A4, Letter and so on) and whether it is password protected. Useful for checking documents before you send them, since metadata often reveals more than you intended.

## Install
Needs `pypdf`:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python pdf_metadata_viewer.py FILE.pdf [FILE.pdf ...] [--json]
```

## Example
```bash
python pdf_metadata_viewer.py report.pdf handbook.pdf
```
```
report.pdf
  bytes      1462
  encrypted  False
  pages      3
  title      Quarterly Report
  author     Ada Lovelace
  creator    Demo Writer
  page size  210 x 297 mm (A4)
handbook.pdf
  bytes      2028
  encrypted  False
  pages      5
  title      Team Handbook
  author     People Team
  page size  210 x 297 mm (A4)
```

## Notes
- Only fields that are present are shown. Many PDFs have no title or author.
- Encrypted files show just their size and encryption status, since the rest can't be read without the password.
- Read-only. To remove or edit metadata you need a PDF editor.
