# top-ips-reporter

## Purpose
Find out who is hitting your web server. The tool reads nginx or Apache access logs and ranks the client IP addresses by number of requests (or by data sent, or by errors), showing each one's share of all traffic, bytes served, number of error responses, when it was active and its most requested page. IPs that sent many requests with mostly errors are flagged, which is the usual signature of scanners and brute-force attempts.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python top_ips_reporter.py access.log [more.log ...] [--top 10] [--by requests|bytes|errors]
                           [--network 24] [--exclude-ip 203.0.113.9 ...]
```
`--network 24` groups addresses into /24 blocks (for IPv6 use a prefix such as `64`), which makes a distributed crawl easy to see. `--exclude-ip` leaves out your own address or monitoring checks (repeat for several). The common and combined log formats are supported; lines in other formats are counted and skipped. The log is only read; the tool never blocks anyone.

## Example
```bash
python top_ips_reporter.py access.log --top 4
```
```
60 request(s) from 8 IP(s). Ranked by requests.

  #  Address        Requests   Share       Data  Errors
  1  198.51.100.23        20   33.3%   461.2 KB       3
       2026-11-10 09:00 to 09:44, most requested: /products/42
  2  203.0.113.7          13   21.7%   304.5 KB       1
       2026-11-10 09:02 to 09:44, most requested: /
  3  192.0.2.44           10   16.7%   211.4 KB       1
       2026-11-10 09:09 to 09:46, most requested: /
  4  192.0.2.5             7   11.7%   219.1 KB       0
       2026-11-10 09:05 to 09:39, most requested: /api/users
... and 4 more.
```

## Notes
- Behind a proxy or CDN the log shows the proxy's address unless your server records the forwarded client address.
- A flagged IP isn't proof of abuse; check what it requested before blocking anything.
- Use `nginx-log-parser` to export the full detail as CSV, and `status-code-counter` for response-code totals.
