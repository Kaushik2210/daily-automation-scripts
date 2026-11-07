# page-title-fetcher

## Purpose
Turn a list of links into readable ones. For each page it reads the `<title>` (and optionally the meta description), so you can label bookmarks, build a link list for a document or spot pages with a missing title.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python page_title_fetcher.py SOURCE [SOURCE ...] [--description] [--csv]
```
A `SOURCE` is a page URL or a saved `.html` file. Pages are fetched several at a time, and only the first 256 KB of each is read. `--csv` prints a table you can open in a spreadsheet. The exit code is 1 if any page couldn't be read.

## Example
```bash
python page_title_fetcher.py page.html page-two.html --description
```
```
ACME Widgets - Home  <-  page.html
    Quality widgets since 1999
Contact ACME  <-  page-two.html
2 of 2 page(s) read.
```

## Notes
- Fetching URLs needs network access; the website demo reads the sample pages.
- Whitespace and line breaks inside titles are collapsed into single spaces.
- Titles set by JavaScript after the page loads are not seen.
