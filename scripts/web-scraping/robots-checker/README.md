# robots-checker

## Purpose
Before scraping or crawling a site, find out what its `robots.txt` allows. Give it URLs and it tells you which are allowed or blocked for your crawler name, which rule decided it, the requested crawl delay and any sitemaps listed.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python robots_checker.py URL [URL ...] [--agent NAME]
python robots_checker.py PATH [PATH ...] --robots robots.txt [--agent NAME]
```
With full URLs it downloads each site's `robots.txt` once. With `--robots` it uses a saved file instead and you can give plain paths such as `/private/page`. The exit code is 1 if anything is blocked.

## Example
```bash
python robots_checker.py /private/public/page /private/secret /admin/panel /products --robots robots.txt
```
```
ALLOWED /private/public/page  (rule: Allow /private/public/)
BLOCKED /private/secret  (rule: Disallow /private)
BLOCKED /admin/panel  (rule: Disallow /admin/)
ALLOWED /products
Crawl-delay for *: 5 seconds between requests.
Sitemaps: https://example.com/sitemap.xml
```

## Notes
- It follows the standard rules: the most specific (longest) matching rule wins, `*` and a trailing `$` are supported, and a crawler-specific group beats the `*` group.
- A missing `robots.txt` (404) means everything is allowed.
- Fetching a real `robots.txt` needs network access; the website demo uses the sample file.
- This is a courtesy check, not permission: sites can also have terms of use.
