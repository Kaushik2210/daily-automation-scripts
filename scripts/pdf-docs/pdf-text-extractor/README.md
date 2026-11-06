# pdf-text-extractor

## Purpose
Get the text out of PDFs so you can search it, quote it or feed it to other tools. By default it prints a short preview of each file; with `--apply` it saves each PDF's full text as a `.txt` file.

## Install
Needs `pypdf`:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python pdf_text_extractor.py FILE.pdf [FILE.pdf ...] [--markers] [--preview N] [-o OUTDIR --apply]
```
`--markers` adds a `--- page N ---` line before each page. `--preview 0` shows the whole text. Without `--apply` nothing is written. With it, `report.pdf` becomes `report.txt` next to the PDF (or in `-o`).

## Example
```bash
python pdf_text_extractor.py report.pdf --markers
```
```
== report.pdf: 3 page(s), 42 word(s)
--- page 1 ---
Quarterly report
Page one: summary of results.
Revenue grew 12 percent.

--- page 2 ---
Page two: details
Costs were flat compared with last quarter.

--- page 3 ---
Page three: outlook
We expect steady growth next quarter.

Preview only. Use --apply to save .txt files.
```

## Notes
- This reads the text layer of the PDF. A scan made of pictures has no text layer, and the tool says so instead of printing nothing.
- Password-protected or damaged files are reported and skipped; the exit code is then 1.
- Layout (columns, tables) is flattened to plain text, so check anything that depends on position.
