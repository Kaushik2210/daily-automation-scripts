# markdown-to-pdf

## Purpose
Turn notes, READMEs and reports written in markdown into a tidy A4 PDF you can print or share. It handles headings, paragraphs, bullet and numbered lists, code blocks and horizontal rules, and tidies links, bold and italics into plain text.

## Install
Needs `fpdf2`:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python markdown_to_pdf.py FILE.md [-o OUTPUT.pdf] [--apply]
```
Dry run by default: it renders in memory and reports how many pages the PDF would have. Pass `--apply` to write `<name>.pdf` (or the file you name with `-o`). An existing file is never overwritten.

## Example
```bash
python markdown_to_pdf.py README.md
```
```
README.md: 9 block(s) -> 1 page(s), 1237 bytes
Dry run: would write README.pdf. Use --apply to do it.
```

## Notes
- It uses the PDF standard fonts, which only cover Western European characters; anything else is replaced with `?`. Curly quotes and dashes are converted to plain ones.
- Tables and images in the markdown are not rendered, only their text.
- For heavily styled documents, a browser's "print to PDF" on rendered HTML will look richer.
