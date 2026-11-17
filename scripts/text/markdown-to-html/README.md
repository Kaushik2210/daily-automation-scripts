# markdown-to-html

## Purpose
Turn a markdown file into a single self-contained web page you can open in a browser, email or publish. It handles headings (with anchor ids), paragraphs, bold/italic/strikethrough, links and images, inline code and fenced code blocks, bullet, numbered and task lists, block quotes, tables and horizontal rules. The page has clean built-in styling that follows the reader's light or dark mode, and all text is HTML-escaped.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python markdown_to_html.py FILE.md [-o OUT.html] [--title TEXT] [--no-style] [--apply]
```
Dry run by default: it converts in memory and reports the title and size. With `--apply` it writes `FILE.html` next to the input (or `-o`) and refuses to overwrite an existing file. The title comes from the first `# heading` unless you pass `--title`.

## Example
```bash
python markdown_to_html.py meeting-notes.md --apply
```
```
meeting-notes.md -> meeting-notes.html: "Team meeting", 1,827 characters, 3 heading(s)
Saved meeting-notes.html.
```

## Notes
- Nested lists and raw HTML blocks are not supported; this is a deliberately small converter for everyday notes and READMEs.
- Use `markdown-to-pdf` when you need a PDF instead.
