# pdf-merger

## Purpose
Combine several PDFs into one document, in exactly the order you list them. Handy for bundling scans, chapters or receipts into a single file. Optional bookmarks make it easy to jump between the original parts.

## Install
Needs `pypdf`:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python pdf_merger.py FILE.pdf FILE.pdf [...] [-o merged.pdf] [--bookmarks] [--apply]
```
Dry run by default: it shows each file's page count and what the result would hold. Pass `--apply` to write the merged file. An existing output file is never overwritten.

## Example
```bash
python pdf_merger.py report.pdf handbook.pdf -o combined.pdf --bookmarks
```
```
report.pdf: 3 page(s)
handbook.pdf: 5 page(s)
Dry run: would write combined.pdf with 8 page(s). Use --apply to do it.
```

## Notes
- The source files are never changed.
- A file that isn't a readable PDF (or is password protected) stops the run with a message naming it.
- To split a PDF again, see `pdf-splitter`.
