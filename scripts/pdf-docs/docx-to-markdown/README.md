# docx-to-markdown

## Purpose
Turn Word documents into clean markdown you can edit in any text editor, commit to git or publish on the web. Unlike a plain-text extractor, it keeps the document's structure: title and headings, **bold** and *italic* text, hyperlinks, bullet and numbered lists (including nested levels) and tables. It reads the `.docx` file directly, so Word does not need to be installed.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python docx_to_markdown.py FILE.docx [FILE.docx ...] [-o OUTDIR]
```
Without `-o` the markdown is printed (with a `<!-- name -->` marker between several files). With `-o` each file is written as `OUTDIR/NAME.md`; existing files are never overwritten. If the document has a Title style, it becomes `#` and Heading 1 becomes `##`. The exit code is 1 if a file can't be read.

## Example
```bash
python docx_to_markdown.py report.docx
```
```
# Quarterly Report

## Summary

Sales grew **12 percent** this quarter, driven by *new customers*. Read the [full dashboard](https://example.com/dashboard).

### Highlights

- Launched the mobile app
- Opened two new offices
- Hired **eight** engineers

### Next steps

1. Finish the audit
2. Plan the next release

| Region | Sales | Growth |
| --- | --- | --- |
| North | 120 | 10% |
| South | 95 | 14% |

Prepared by the finance team.
```

## Notes
- Images, comments, footnotes and text boxes are not converted; use `docx-text-extractor` if you only need the text.
- Old `.doc` files must be saved as `.docx` first.
- Convert the result to a web page with `markdown-to-html`.
