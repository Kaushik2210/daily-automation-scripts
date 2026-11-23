# rate-limited-fetcher

## Purpose
Fetch web pages the way a considerate visitor would. The tool keeps a minimum gap between requests to the same website (so `--rate 1` means at most one request per second per site), and when a server pushes back it **backs off**: on a 429 or 5xx answer or a network error it waits and tries again, pausing longer each time (1s, 2s, 4s... with a little random jitter so many clients don't all return at once). If the server sends a `Retry-After` header, that exact wait is used instead. Responses can be saved to a folder.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python rate_limited_fetcher.py urls.txt [https://more.example/page] [--rate 1] [--retries 3] [--backoff 1]
                               [--timeout 15] [-o pages] [--apply]
```
URLs can be given directly or in text files with one per line (`#` starts a comment). **Dry run by default:** it prints the schedule (when each request would start) and an estimate of the total time, and makes no request. Add `--apply` to fetch. Successful pages are saved into `-o` (existing files are never overwritten). The exit code is 1 if any URL ultimately failed. Always check a site's terms and `robots.txt` first, and keep the rate low; see `sitemap-crawler` for a robots-aware crawl.

## Example
```bash
python rate_limited_fetcher.py urls.txt --rate 2
```
```
4 URL(s) on 3 site(s), 2 request(s)/second per site, up to 3 retries (1 invalid skipped)
  t+  0.0s  https://example.com
  t+  0.5s  https://example.com/
  t+  0.0s  https://www.python.org/
  t+  0.0s  http://example.org/page?utm_source=news&id=7

Plan only: about 0.5s without retries (retries wait 1s, 2s, 4s... or the server's Retry-After). Use --apply to fetch.
```

## Notes
- Statuses that are retried: 408, 425, 429, 500, 502, 503, 504, and network errors. Other 4xx answers (such as 404) are final.
- The limit is per site, so URLs on different sites are fetched without waiting for each other.
- Use `async-url-checker` when you only need to know whether URLs work, and `parallel-downloader` for big files.
- The website demo shows the plan; fetching works on your own computer.
