# html-table-extractor

## Purpose
Turn the tables on a web page into spreadsheets. It finds every `<table>` in a page or saved HTML file, shows you a preview of each, and (when you ask) writes them out as CSV files that open straight in Excel or Google Sheets. Header cells, captions and `colspan` are handled for you.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python html_table_extractor.py SOURCE [--table N ...] [--out-dir DIR] [--preview ROWS] [--apply]
```
By default it only shows what it would write. Add `--apply` to create `<name>-table-<N>.csv` files in the output folder. Existing files are never overwritten.

## Example
```bash
python html_table_extractor.py tables.html --preview 2
```
```
Table 1 (Sales by region): 4 row(s) x 3 column(s)
   Region | Q1 | Q2
   North | 1,200 | 1,450
   would write tables-table-1.csv
Table 2 (untitled): 3 row(s) x 2 column(s)
   Name | Role
   Asha & Co | Lead
   would write tables-table-2.csv
Dry run - nothing written. Add --apply to create the CSV files.
```

## Notes
- Tables nested inside other tables are exported as their own tables; their text is not repeated in the outer cell.
- A cell that spans several columns is padded with empty cells so every row has the same width.
- Pages that fill their tables with JavaScript won't show them here; save the page after it has loaded and use that file instead.
- On the website demo only saved files can be read, and the CSV files are written into your browser's temporary folder.
