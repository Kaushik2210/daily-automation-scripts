# web-scraper

## Purpose
Pull exactly the bits you want out of a web page. Give it one or more CSS selectors and it prints the text (or an attribute such as `href`) of every match, as plain text, JSON or CSV. When you point it at a live URL it reads the site's `robots.txt` first and politely refuses to fetch pages the site has asked bots to stay away from.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python web_scraper.py SOURCE -s "[NAME=]CSS" [-s ...] [--attr href] [--format text|json|csv]
                      [--limit N] [--base URL] [--robots-file robots.txt]
```
`SOURCE` is a URL or a saved `.html` file. Selectors support tags, `.class`, `#id`, `[attr]`, `[attr=value]` (also `^=`, `$=`, `*=`), the descendant and `>` combinators, and comma lists. Give a selector a name with `price=li b` and the CSV gets a column for it. The exit code is 2 when `robots.txt` disallows the page and 1 when nothing matched.

## Example
```bash
python web_scraper.py page.html -s "link=a" -s "internal=nav a" --attr href --base https://example.com/
```
```
[link] https://example.com/products
[link] https://example.com/about.html
[link] https://example.com/docs
[link] https://example.com/#top
[link] mailto:hello@example.com
[link] https://example.com/docs
[link] https://partner.test/page
[link] javascript:void(0)
[internal] https://example.com/products
[internal] https://example.com/about.html
[internal] https://example.com/docs
[internal] https://example.com/#top
```

## Notes
- Only one page is fetched per run, with an honest `User-Agent`. Scraping is polite, not stealthy: if a site forbids it, the tool stops.
- Selectors with spaces inside attribute values (`[title="a b"]`) are not supported.
- Pages that build their content with JavaScript aren't rendered; you only get the HTML the server sends.
- On the website demo only saved files can be scraped; fetching URLs works on your own computer.
