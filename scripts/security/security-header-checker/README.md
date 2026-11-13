# security-header-checker

## Purpose
Find out how well a website protects its visitors through its HTTP response headers. The tool grades a site from A+ to F and explains each check in plain language: HSTS (forces HTTPS), Content-Security-Policy (blocks injected scripts, and is marked down for `unsafe-inline` and wildcards), clickjacking protection, `nosniff`, Referrer-Policy, Permissions-Policy, cross-origin isolation, cookie flags (`Secure`, `HttpOnly`, `SameSite`) and whether the server advertises its software version. Each line says what's missing and how many points it cost.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python security_header_checker.py https://example.com [--min-grade C]
python security_header_checker.py saved-headers.txt
```
Give a URL (the page is requested once and only its headers are read) or a saved dump such as the output of `curl -sI -L https://example.com > headers.txt`; for a redirect chain the final response is graded. The exit code is 1 when the grade is worse than `--min-grade` (C by default), which makes it usable as a CI check for your own site. Only request sites you own or are allowed to test.

## Example
```bash
python security_header_checker.py site-headers.txt
```
```
Security headers: grade C (64%)

  [PASS] HSTS                     20/20  HSTS enabled for 365 days
  [WARN] Content-Security-Policy  15/25  CSP allows 'unsafe-inline', which weakens it
  [PASS] Clickjacking             10/10  Framing is restricted (clickjacking protection)
  [PASS] MIME sniffing            10/10  X-Content-Type-Options: nosniff
  [WARN] Referrer-Policy           5/10  Referrer-Policy 'no-referrer-when-downgrade' still leaks full URLs to other sites
  [FAIL] Permissions-Policy        0/5   No Permissions-Policy (camera, microphone, location... aren't restricted)
  [FAIL] Isolation                 0/5   No Cross-Origin-Opener-Policy / Cross-Origin-Resource-Policy
  [WARN] Cookies                   4/10  session lacks Secure/SameSite; theme lacks HttpOnly
  [WARN] Info disclosure           0/5   Reveals software details: Server: nginx/1.24.0, X-Powered-By: Express
```

## Notes
- The score is a guide, not a certificate: a site can score A+ and still have other weaknesses, and a low score doesn't mean it has been hacked.
- Weights: CSP 25, HSTS 20, and 10 each for framing, `nosniff`, referrer policy and cookies; the rest 5.
- Use `header-inspector` to see every header, and `ssl-expiry-checker` for the certificate.
- The website demo grades saved header files; checking a live site works on your own computer.
