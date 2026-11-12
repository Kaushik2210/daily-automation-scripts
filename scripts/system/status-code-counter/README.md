# status-code-counter

## Purpose
A quick health check for a website from its access log. The tool counts every HTTP status code (200, 301, 404, 500...) with its plain-English meaning, share of traffic and a bar, then rolls them up by class (success, redirect, client error, server error). For each error code it lists the pages responsible, so a spike of 404s or 500s points straight at the broken URL. It can also act as a guard in a script: `--fail-above-5xx` exits with 1 when too many requests ended in a server error.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python status_code_counter.py access.log [more.log ...] [--method POST] [--path-contains /api]
                              [--top-paths 3] [--fail-above-5xx 1.0]
```
`--method` and `--path-contains` narrow the count to part of your traffic. Query strings are removed from the paths shown, so `/missing?ref=1` and `/missing?ref=2` are the same page. `--top-paths 0` hides the error breakdown. Common and combined log formats are supported; other lines are counted and skipped. The log is only read.

## Example
```bash
python status_code_counter.py access.log
```
```
60 request(s)

By status code:
  200 OK                         50   83.3%  ########################
  304 Not Modified                4    6.7%  ##
  401 Unauthorized                1    1.7%  #
  403 Forbidden                   2    3.3%  #
  404 Not Found                   1    1.7%  #
  500 Internal Server Error       2    3.3%  #

By class:
  2xx success            50   83.3%
  3xx redirect            4    6.7%
  4xx client error        4    6.7%
  5xx server error        2    3.3%

Paths behind the errors:
  401: /admin (1)
  403: /admin (2)
  404: /missing-page (1)
  500: /api/orders (2)

Client errors: 6.7%   Server errors: 3.3%
```

## Notes
- A 304 "Not Modified" is normal for cached files and counts as a redirect class.
- Bots probing for `/admin` or `/wp-login.php` produce many harmless 404s; look at which paths they are before worrying.
- Use `top-ips-reporter` to see who is behind the errors.
