# broken-link-finder

## Purpose
Catch dead links before your visitors do. It reads one page, collects every link on it and checks each one, listing the ones that return an error or don't answer at all. Handy for a website you maintain or documentation you publish.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python broken_link_finder.py PAGE_URL [--only internal|external] [--max N] [--delay SEC] [--plan]
python broken_link_finder.py saved.html --base https://example.com/ --plan
```
A saved `.html` file needs `--base` so relative links can be resolved. `--plan` lists the links that would be checked without sending any request. `--delay` waits between requests (and checks one at a time), which is kinder to small servers. The exit code is 1 when any link is broken.

## Example
```bash
python broken_link_finder.py page.html --base https://example.com/ --plan
```
```
WOULD CHECK  https://example.com/products
WOULD CHECK  https://example.com/about.html
WOULD CHECK  https://example.com/docs
WOULD CHECK  https://partner.test/page
Would check 4 link(s) found on page.html.
```

## Notes
- Checking links needs network access, so the website demo can only run `--plan`. Run the real check on your own computer.
- It checks the links on a single page, not a whole site, and stops at 100 links unless you raise `--max`.
- Only check sites you own or have permission to test. Some sites block automated checks and may report a working link as broken.
