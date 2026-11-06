# docx-text-extractor

## Purpose
Read Word documents without Word. It pulls out the text in order, including bullet points and tables, and can keep headings, bullets and tables as markdown so the result drops straight into notes, a wiki or a search index.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python docx_text_extractor.py FILE.docx [FILE.docx ...] [--markdown] [-o OUTDIR --apply]
```
The text is printed; with `--apply` each document is saved as `<name>.txt` (or `<name>.md` with `--markdown`) next to it or in `-o`.

## Example
```bash
python docx_text_extractor.py contract.docx --markdown
```
```
== contract.docx: 44 word(s)
# Service Agreement

This agreement is made between Demo Corp and the client.

Payment is due within 30 days of the invoice date.

- Confidentiality applies to both parties.

| Item | Price |
| --- | --- |
| Consulting | $1,200 |

Preview only. Use --apply to save the text to files.
```

## Notes
- Only the modern `.docx` format is supported, not the old `.doc`.
- Headers, footers, footnotes and text boxes are not included, only the main body.
- It never opens the file in Word, so macros cannot run. Very large documents are refused.
