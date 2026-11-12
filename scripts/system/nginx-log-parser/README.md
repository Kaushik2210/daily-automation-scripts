# nginx-log-parser

## Purpose
Turn a web server access log into a spreadsheet. The tool reads nginx or Apache logs in the common and combined formats and writes a clean CSV with one row per request: time (ISO 8601 with its time zone), client IP, method, path, protocol, status, bytes sent, referrer, user agent and user. Open the result in Excel or Google Sheets, or load it into pandas, SQLite or any analysis tool. Lines that aren't in the expected format are counted and skipped rather than breaking the run.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python nginx_log_parser.py access.log [more.log ...] [--out requests.csv] [--status 5xx] [--method POST]
                           [--path-contains /api] [--columns time,ip,status,path]
```
Without `--out` the CSV is printed (the summary goes to stderr so it doesn't mix with the data); with it a new file is written and an existing file is never overwritten. `--status` takes an exact code (`404`) or a class (`5xx`). `--columns` picks and orders the columns from: `time, ip, method, path, protocol, status, bytes, referrer, user_agent, user`. The exit code is 1 when no rows matched. This handles the default `combined` log format; custom `log_format` lines with extra fields need a small change to the pattern.

## Example
```bash
python nginx_log_parser.py access.log --status 5xx --columns time,ip,method,path,status
```
```
time,ip,method,path,status
2026-11-10T09:00:49+00:00,198.51.100.23,POST,/api/orders,500
2026-11-10T09:14:13+00:00,198.18.0.12,POST,/api/orders,500
```

## Notes
- A dash (`-`) in the log becomes an empty cell, and a missing byte count becomes 0.
- Plain-text logs only; unzip rotated `.gz` files first (`gunzip access.log.1.gz`).
- Pair it with `top-ips-reporter` and `status-code-counter` for quick summaries without leaving the terminal.
