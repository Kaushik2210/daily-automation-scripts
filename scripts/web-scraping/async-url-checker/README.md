# async-url-checker

## Purpose
Check a very long list of web addresses quickly and politely. The tool uses Python's `asyncio` to keep many requests in flight at once (50 by default), with a separate limit per website (5) so one server is never hammered. For each URL it reports the final status, the response time and where redirects lead, retries short-lived failures (5xx errors and network hiccups) with a growing pause, and sums everything up. It can save the results to a CSV file and later summarise that file without touching the network again.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python async_url_checker.py urls.txt [more.txt https://extra.example/] [--concurrency 50] [--per-host 5]
                            [--timeout 10] [--retries 1] [--method HEAD|GET] [--no-follow]
                            [--only-problems] [--csv results.csv]
python async_url_checker.py --plan urls.txt
python async_url_checker.py --summarise results.csv [--slow 2000] [--only-problems]
```
Inputs are URLs or text files with one URL per line (`#` starts a comment); duplicates and invalid lines are removed and counted. `HEAD` requests (the default) are fast and fall back to `GET` for servers that refuse them. `--plan` only validates the list. `--csv` saves `url,status,ms,final_url,error` to a new file (never overwriting). The exit code is 1 if any URL is broken, so it works as a link check in CI. Only check sites you own or are allowed to test, and keep the limits modest.

## Example
```bash
python async_url_checker.py --summarise link-check-results.csv
```
```
OK            200    84 ms  https://example.com/  
OK            200   131 ms  https://example.com/products  
REDIRECT      301    62 ms  https://example.com/old-page  -> https://example.com/new-page
CLIENT ERROR  404    77 ms  https://example.com/missing  HTTP 404
OK            200   210 ms  https://www.python.org/  
OK            200  2450 ms  https://slow.example.net/report    (slow)
FAILED          0      ---  https://down.example.org/  connection refused
SERVER ERROR  503   320 ms  https://example.com/api/health  HTTP 503
OK            200    96 ms  https://example.com/about  

9 URL(s): 5 ok, 1 redirect, 1 client error, 1 server error, 1 failed.
Response times: median 131 ms, slowest 2450 ms.
```

## Notes
- Statuses: OK, REDIRECT (the final address differs), CLIENT ERROR (4xx), SERVER ERROR (5xx) and FAILED (no answer).
- Requests run in worker threads managed by asyncio, so no extra libraries are needed.
- Use `bulk-url-checker` for a simpler thread-pool version and `broken-link-finder` to find links inside a page.
- The website demo summarises a saved results file; checking live URLs works on your own computer.
