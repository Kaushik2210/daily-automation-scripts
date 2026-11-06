# pdf-page-counter

## Purpose
Find out how many pages a stack of PDFs adds up to, for example before printing, estimating translation work or checking an upload limit. It lists each file with its page count and size, then the grand total.

## Install
Needs `pypdf`:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python pdf_page_counter.py PATH [PATH ...] [-r]
```
`PATH` can be PDF files or folders. Folders are searched for `.pdf` files, including subfolders when you pass `-r`. The exit code is 1 if any file had to be skipped.

## Example
```bash
python pdf_page_counter.py report.pdf handbook.pdf scan_0001.pdf
```
```
report.pdf         3 page(s)     1.4 KB
handbook.pdf       5 page(s)     2.0 KB
scan_0001.pdf      1 page(s)      679 B
3 PDF(s), 9 page(s) in total.
```

## Notes
- Password-protected and damaged files are reported as skipped instead of stopping the run.
- Sizes are the files' sizes on disk.
- Read-only.
