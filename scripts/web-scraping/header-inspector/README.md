# header-inspector

## Purpose
See what a web server says about itself. It prints a URL's HTTP response headers in a tidy table and adds plain-English notes: the content type and size, how long browsers may cache it, where it redirects, what software it announces, how many cookies it sets and whether HSTS (forced HTTPS) is on.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python header_inspector.py URL [--follow]
python header_inspector.py saved-headers.txt
```
For a URL it sends one `HEAD` request and shows the first response, so a redirect shows its `Location` instead of being followed (add `--follow` to follow it). You can also read a saved dump, for example one made with `curl -I https://example.com > saved-headers.txt`.

## Example
```bash
python header_inspector.py headers.txt
```
```
HTTP/2 200
  content-type               text/html; charset=utf-8
  server                     nginx/1.24
  cache-control              max-age=3600
  content-length             18211
  strict-transport-security  max-age=31536000; includeSubDomains
  x-powered-by               Express
  set-cookie                 session=abc123; HttpOnly
  set-cookie                 theme=dark; Path=/
  x-content-type-options     nosniff

Notes:
  - Content: text/html (17.8 KB)
  - Caching: reusable for 1 hour
  - Server software announced: nginx/1.24
  - Technology revealed by X-Powered-By: Express
  - Sets 2 cookies
  - HSTS is on
```

## Notes
- Requesting a URL needs network access; the website demo reads the sample file.
- Repeated headers such as `set-cookie` are all shown.
- Read-only. Only inspect sites you are allowed to; for a full security review see the security tools later in this challenge.
