# pdf-splitter

## Purpose
Pull pages out of a PDF. Either extract a selection (such as pages 1 to 3 and 5) into one new file, or break the whole document into parts of a fixed size, down to one file per page.

## Install
Needs `pypdf`:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python pdf_splitter.py FILE.pdf --pages 1-3,5,8- [-o OUTDIR] [--apply]
python pdf_splitter.py FILE.pdf --every N [-o OUTDIR] [--apply]
```
Use exactly one of `--pages` or `--every`. Page numbers start at 1, and `8-` means page 8 to the end. Dry run by default: it lists the files it would create. Pass `--apply` to write them next to the original (or into `-o`).

## Example
```bash
python pdf_splitter.py handbook.pdf --every 2
```
```
handbook_part001.pdf  (pages 1-2 of 5)
handbook_part002.pdf  (pages 3-4 of 5)
handbook_part003.pdf  (page 5 of 5)
Would write 3 file(s). Use --apply to do it.
```

## Notes
- The original PDF is never changed.
- Output names are `<name>_pages_<ranges>.pdf` or `<name>_part001.pdf`, `<name>_part002.pdf` and so on.
- A page number outside the document stops the run with a clear message.
