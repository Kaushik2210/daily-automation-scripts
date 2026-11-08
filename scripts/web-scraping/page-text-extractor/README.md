# page-text-extractor

## Purpose
Read an article without the clutter. The tool finds the main content of a web page (the `<article>` or `<main>` part when there is one), drops menus, footers, sidebars, forms, scripts and styles, and prints clean, wrapped text with headings and bullet points kept in a Markdown-like layout. It also tells you the word count and a rough reading time.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python page_text_extractor.py SOURCE [--width 80] [--out article.txt]
```
`SOURCE` is a URL or a saved `.html` file. With `--out` the text is saved to a new file (an existing file is never overwritten).

## Example
```bash
python page_text_extractor.py article.html --width 70
```
```
Why small scripts win - Example Blog
(71 words, about 1 min read)

# Why small scripts win

By Sam Writer

Small scripts are easy to read, easy to test and easy to throw away
when they stop being useful. A script that does one thing well can be
understood in a single sitting.

## Three habits

- Name things plainly
- Print what you did
- Keep a dry-run mode

Start with the smallest version that solves your problem and grow from
there.
```

## Notes
- If the page has no `<article>` or `<main>` element the whole page is used, minus the obvious clutter, so results on unusual layouts may include extra lines.
- Reading time assumes about 220 words per minute.
- Pages that need JavaScript to show their content come out empty; save the page from your browser after it loads and use that file.
- Respect copyright: keep saved text for your own reading unless the licence says otherwise.
- The website demo only reads saved files; URLs work on your own computer.
