# bulk-url-checker

## Purpose
Find out which links in a list still work. Every URL gets its HTTP status, response time and the final address after redirects, and the run exits with 1 if anything is broken, so it works in scheduled checks and CI.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python bulk_url_checker.py URL_OR_FILE [URL_OR_FILE ...] [--plan] [--timeout SEC] [--workers N]
```
Pass URLs directly or text files with one URL per line (`#` starts a comment). Duplicates are removed (`https://Example.com` and `https://example.com/` count as one). `--plan` only lists what would be checked and sends nothing. Requests run several at a time, politely, with a `HEAD` request first and `GET` only if the server refuses `HEAD`.

## Example
```bash
python bulk_url_checker.py urls.txt --plan
```
```
SKIP  not an http(s) URL: not a url
WOULD CHECK  https://example.com/
WOULD CHECK  https://www.python.org/
WOULD CHECK  http://example.org/page?utm_source=news&id=7
Would check 3 URL(s); 1 invalid, 2 duplicate(s) removed.
```

## Notes
- Checking URLs needs network access, so the website demo can only run the `--plan` mode; run the real check on your own computer.
- Only check sites you are allowed to; keep `--workers` low for small servers.
- A timeout or connection failure is reported as `FAIL` with the reason.
