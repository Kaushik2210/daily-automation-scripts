# link-extractor

## Purpose
See every link on a page at a glance. It lists each unique link with its visible text, tells internal links from external ones, and marks links with `rel="nofollow"`. Useful for audits, migrations and finding what a page points to.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python link_extractor.py URL_OR_FILE [--base PAGE_URL] [--only internal|external]
```
Give a page address to download it, or a saved `.html` file (add `--base` so relative links such as `/products` can be turned into full addresses and classified). Links like `mailto:`, `tel:`, `javascript:` and `#anchors` are skipped, and repeated links appear once.

## Example
```bash
python link_extractor.py page.html --base https://example.com/
```
```
internal  https://example.com/products  'Products'
internal  https://example.com/about.html  'About us'
internal  https://example.com/docs  'Docs'
external  https://partner.test/page  'partner' [nofollow]
4 unique link(s): 3 internal, 1 external.
```

## Notes
- Downloading a page needs network access. The website demo works from the sample saved page; with a real URL, run it on your own computer.
- Pages are read up to 2 MB. Links added later by JavaScript are not seen, because the page is not run.
- Read-only.
