# health-check-poller

## Purpose
Check whether your services are really up, not just once but over a short period. The tool requests each health-check URL several times, records the status code and response time, and tells you for every URL whether it is **UP**, **SLOW**, **DEGRADED** (some checks failed) or **DOWN**, with the uptime percentage, average and slowest response, and the last error. It can also require a specific status (`200`, `2xx`, `204`...) or a piece of text in the response.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python health_check_poller.py URL [URL ...] [--count 3] [--interval 2] [--timeout 5] \
    [--expect 2xx] [--contains TEXT] [--slow 1000] [--csv log.csv]
python health_check_poller.py --summarise log.csv
```
Each round checks every URL once, then waits `--interval` seconds. `--csv` appends every check to a log file (creating it with a header if needed), and `--summarise` reads such a log later and prints the same summary without polling, which is handy for a report over many runs. The exit code is 1 when any URL is not UP, so it works in deployment scripts. Only poll services you own or are allowed to test.

## Example
```bash
python health_check_poller.py --summarise health-results.csv
```
```
Summary:
  DEGRADED https://example.com/health  5/6 ok (83%), avg 368 ms, max 1210 ms  last error: HTTP 503
  UP       https://api.example.com/ping  6/6 ok (100%), avg 39 ms, max 44 ms
  DOWN     https://legacy.example.com/status  0/3 ok (0%), no response  last error: connection refused
```

## Notes
- A response slower than `--slow` milliseconds makes a URL SLOW even if it returned 200.
- Redirects are followed; connection errors and timeouts count as failures with the error text.
- The website demo summarises a saved log; polling live URLs works on your own computer.
