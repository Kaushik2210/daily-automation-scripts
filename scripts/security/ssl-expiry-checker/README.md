# ssl-expiry-checker

## Purpose
Never be surprised by an expired certificate. Give the tool a list of domains (or saved certificate files) and it reads each site's TLS certificate, then reports when it expires, how many days are left, who issued it, and whether the certificate actually covers the domain name. Each is marked OK, EXPIRING SOON, EXPIRED or NAME MISMATCH, and the exit code is 1 when anything needs attention, so a scheduled run can alert you.

## Install
Standard library only, Python 3.11+. Nothing to install. The certificate is decoded by a small built-in parser, so no extra crypto package is needed.

## Usage
```bash
python ssl_expiry_checker.py example.com example.org:8443 [--warn-days 30] [--timeout 8]
python ssl_expiry_checker.py site.pem fullchain.pem
```
`domain` connects on port 443 and `domain:port` on another port. A file ending in `.pem`, `.crt` or `.cer` is read directly (for a bundle, the first certificate, which is the site's own). The tool reads the certificate the server presents without rejecting it, so even an already-expired certificate can be examined and reported. It only reads; nothing is sent beyond the normal TLS handshake.

## Example
```bash
python ssl_expiry_checker.py fullchain.pem expired.pem expiring.pem --today 2026-11-13
```
```
OK             fullchain.pem            expires 2027-01-01 (49 day(s) left)
               subject example.com; issuer Demo Intermediate CA 1
               names   example.com, www.example.com
EXPIRED        expired.pem              expires 2026-01-01 (316 day(s) ago)
               subject old.example.org; issuer Demo Intermediate CA 1
               names   old.example.org
EXPIRING SOON  expiring.pem             expires 2026-11-25 (12 day(s) left)
               subject shop.example.net; issuer Demo Intermediate CA 1
               names   shop.example.net
```

## Notes
- `--warn-days` sets how early to warn (30 by default). `--today` exists only so examples and tests are repeatable.
- Names are matched against the certificate's Subject Alternative Names, including `*.example.com` wildcards (which cover one level only).
- This checks dates and names, not the whole trust chain; `cert-chain-viewer` shows the chain.
- The website demo reads the sample certificate files; live checks work on your own computer.
