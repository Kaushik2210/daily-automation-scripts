# bookmark-deduper

## Purpose
Clean up a bookmark collection that has grown messy over the years. Export your bookmarks from your browser as an HTML file and the tool finds the ones that point to the same page, even when the address is written differently (`http` vs `https`, `www.` or not, a trailing slash, a `#fragment`, tracking parameters like `utm_source` and `fbclid`). By default it only lists the duplicates; with `--apply` it saves a cleaned copy and leaves your original untouched.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python bookmark_deduper.py bookmarks.html                              # show the duplicates
python bookmark_deduper.py bookmarks.html --out cleaned.html --apply   # save a clean copy
```
In Chrome, Edge, Firefox and Safari use "Export bookmarks" from the bookmark manager to get the HTML file, and "Import bookmarks" to load `cleaned.html` afterwards. The first copy of each page is kept (in folder order) and later copies are removed, together with their description lines. Different query strings such as `?page=2` count as different pages. The output is a new file; an existing file is never overwritten.

## Example
```bash
python bookmark_deduper.py bookmarks.html
```
```
9 bookmark(s): 5 unique, 4 duplicate(s).
  duplicate (line 14) Python Documentation
    same page as line 8: Python docs
  duplicate (line 15) HN front page
    same page as line 10: Hacker News
  duplicate (line 17) An article again
    same page as line 16: An article
  duplicate (line 19) Hello World repo
    same page as line 9: Hello World

Dry run - nothing written. Add --out FILE --apply to save a cleaned copy.
```

## Notes
- Folders that end up empty are kept; delete them in your browser if you like.
- Non-web links (`mailto:`, `javascript:`) are compared exactly as written.
- Always keep the original export until you've checked the cleaned file imports well.
