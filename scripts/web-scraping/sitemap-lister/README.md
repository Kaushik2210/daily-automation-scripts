# sitemap-lister

## Purpose
Get a clean list of every page a site publishes. It reads a `sitemap.xml` (or the sitemap index that points to several), shows each URL with its last-modified date and lets you filter by text or by date. A good starting point for audits, redirects and crawl planning.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python sitemap_lister.py SITEMAP [--contains TEXT] [--newer-than YYYY-MM-DD] [--limit N] [--csv]
```
`SITEMAP` is a sitemap URL or a saved `.xml` file. A sitemap index lists its child sitemaps; run the tool on each child to see the pages. `--csv` prints a table for a spreadsheet.

## Example
```bash
python sitemap_lister.py sitemap.xml --newer-than 2025-12-01
```
```
2026-01-10  https://example.com/
2026-01-08  https://example.com/products
2025-12-20  https://example.com/products/widget-a
3 of 5 URL(s).
```

## Notes
- Downloading a sitemap needs network access; the website demo reads the sample file.
- Dates are taken from the `lastmod` field, which not every site fills in; undated entries are hidden when you filter by date.
- Sitemaps containing a DOCTYPE or entity definitions are refused, which protects against malicious XML.
