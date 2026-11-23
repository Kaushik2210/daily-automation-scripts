# log-to-sqlite

## Purpose
Turn log files into something you can ask questions of. The tool reads web-server access logs (the common Apache/nginx "combined" format) and application logs (`2026-11-10 08:40:09,475 WARNING [api] message`), recognises each line automatically and stores it in a SQLite database with proper columns: time, IP, method, path, status and bytes for access logs; time, level, component and message for application logs. Stack traces that follow an error line are attached to that error's message. Then use SQL ("which pages returned errors?", "how many warnings per hour?").

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python log_to_sqlite.py app.log access.log --db logs.db [--replace] [--apply]
```
Two tables are used: `access_logs` and `app_logs`. **Dry run by default:** it only reports how many lines of each kind it found (and how many it didn't recognise). With `--apply` the rows are added; new files are appended to what is already there, or use `--replace` to start the tables from scratch. Timestamps are stored as ISO text (`2026-11-10T09:00:06`), so SQL can sort and filter them. After loading it prints a short summary. Query the result with `sqlite-query-cli`.

## Example
```bash
python log_to_sqlite.py app.log access.log --db logs.db --apply
```
```
app.log: 0 access line(s), 42 application line(s)
access.log: 60 access line(s), 0 application line(s)

Saved to logs.db:
  access_logs: 60 row(s)
  app_logs: 42 row(s)
    INFO      22
    WARNING   10
    ERROR     6
    DEBUG     3
    CRITICAL  1
    status codes: 200 x50, 304 x4, 500 x2, 403 x2

Try: sqlite_query_cli.py logs.db "SELECT path, COUNT(*) FROM access_logs WHERE status >= 500 GROUP BY path"
```

## Notes
- Running `--apply` twice on the same files adds the rows twice; use `--replace` to reload.
- Lines that match no known format (and aren't part of a stack trace) are counted but not stored.
- For quick reports without a database, see `log-analyzer`, `nginx-log-parser` and `top-ips-reporter`.
