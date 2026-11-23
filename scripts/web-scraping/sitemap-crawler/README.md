# sitemap-crawler

## Purpose
Explore a website through its sitemap while following its rules. The tool reads a `sitemap.xml` (or a sitemap index), reads the site's `robots.txt`, and lists every page marked **allowed** or **BLOCKED** for your crawler name. It applies the rules the way search engines do: the most specific matching rule wins, `Allow` beats `Disallow` when equally specific, `*` and `$` work in patterns, and the group for the most specific user-agent is used. It also reports the requested `Crawl-delay` and the sitemaps declared in robots.txt. Add `--fetch` to visit the allowed pages one at a time, with a polite delay.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python sitemap_crawler.py --sitemap https://example.com/sitemap.xml [--robots URL_OR_FILE] [--agent MyBot]
                          [--limit 50] [--follow-index] [--fetch] [--delay 1]
python sitemap_crawler.py --sitemap sitemap.xml --robots robots.txt
```
The sitemap and robots.txt can be URLs or saved files, so you can check rules offline. For a URL sitemap, the site's own `/robots.txt` is read automatically. `.gz` sitemaps are unpacked. A sitemap index lists its sub-sitemaps; `--follow-index` reads them too (one request each). Pages on other hosts are skipped. With `--fetch` the delay between requests is `--delay` or the robots `Crawl-delay`, whichever is larger, and each visit shows the status, time, size and page title. Blocked pages are never requested. Only crawl sites you are allowed to crawl.

## Example
```bash
python sitemap_crawler.py --sitemap sitemap-full.xml --robots robots.txt
```
```
10 URL(s) in the sitemap, robots rules for '*'
  allowed     https://example.com/
  allowed     https://example.com/products
  allowed     https://example.com/products/widget-a
  allowed     https://example.com/blog/launch
  BLOCKED     https://example.com/admin/dashboard
  BLOCKED     https://example.com/private/notes
  allowed     https://example.com/private/public/faq
  allowed     https://example.com/about
  allowed     https://example.com/contact
  BLOCKED     https://example.com/admin/users

7 allowed, 3 blocked by robots.txt.
robots.txt asks for a Crawl-delay of 5.0s; using 5s between requests.
Sitemaps declared in robots.txt: https://example.com/sitemap.xml
Use --fetch to visit the allowed pages (one at a time, politely).
```

## Notes
- A missing robots.txt means "everything allowed", with a note.
- This is not a full crawler: it visits the sitemap's pages only and doesn't follow links (see `link-graph-builder`).
- Use `robots-checker` to test a single URL and `sitemap-lister` to just list a sitemap.
- The website demo checks saved files; fetching pages works on your own computer.
