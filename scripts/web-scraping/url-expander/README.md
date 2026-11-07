# url-expander

## Purpose
See where a link really goes before you click it. It follows the redirects of short links (bit.ly style) and tracking links one hop at a time, reports the final address and can strip tracking parameters such as `utm_source` and `fbclid` to give you a clean URL.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python url_expander.py URL [URL ...] [--clean] [--chain] [--max-hops N] [--no-follow]
```
By default each URL is followed through its redirects. `--chain` lists every hop with its HTTP status, `--clean` removes tracking parameters from the final address, and `--no-follow` skips the network entirely and only cleans the URL you gave. Redirect loops and over-long chains are detected and reported.

## Example
```bash
python url_expander.py "http://Example.org/page?utm_source=news&id=7&fbclid=abc" --clean --no-follow
```
```
http://Example.org/page?utm_source=news&id=7&fbclid=abc
  -> http://example.org/page?id=7
```

## Notes
- Following links needs network access, so the website demo runs the `--no-follow` cleaning mode. Following redirects works on your own computer.
- The tool only asks the server for headers and never downloads the page.
- Only the tracking parameters it knows are removed; the rest of the query string is kept as it was.
