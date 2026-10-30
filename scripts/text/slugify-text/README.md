# slugify-text

## Purpose
Convert titles, headings or file names into slugs that are safe in URLs: lowercase, no accents, no punctuation, words joined by a dash.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python slugify_text.py [TEXT ...] [--sep CHAR] [--max-length N] [--keep-case]
```
With no text it reads lines from standard input.

## Example
```bash
python slugify_text.py "Crème Brûlée & Café" "Hello, World!" "Hello, World!"
```
```
creme-brulee-and-cafe
hello-world
hello-world-2
```

## Notes
- Accented letters become their plain equivalents; characters with no plain form are dropped.
- `--max-length` cuts at a word boundary so slugs never end mid-word.
- Repeated titles get `-2`, `-3` and so on, so every slug in a run is unique.
