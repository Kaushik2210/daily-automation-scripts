# error-extractor

## Purpose
Get straight to what went wrong. The tool scans log files for error entries and prints each one with a few lines of context before it and its whole stack trace after it (the untimestamped lines that follow), merging overlapping entries so nothing is printed twice. Matching lines are marked with `>` and show their line numbers, like `grep` but aware of how log entries are laid out.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python error_extractor.py app.log [more.log ...] [--levels ERROR,CRITICAL] [--before 2] [--after 0]
python error_extractor.py app.log --pattern "timeout|refused" -i
python error_extractor.py app.log --count
python error_extractor.py app.log --out errors.txt
```
By default an entry is extracted when its timestamped line has the level ERROR, CRITICAL, FATAL or SEVERE; `--levels` changes that (for example `WARNING,ERROR`). `--pattern` extracts lines matching a regular expression instead. `--before` and `--after` add plain lines of context (the stack trace is always included). `--out` writes the result to a new file and never overwrites an existing one. The exit code is 1 when nothing matched, which suits scheduled checks. Log files are only read.

## Example
```bash
python error_extractor.py app.log --before 1
```
```
   8  2026-11-10 09:03:53,289 WARNING  [api] disk usage at 302%
>  9  2026-11-10 09:06:45,240 ERROR    [worker] database connection refused
  10  Traceback (most recent call last):
  11    File "/srv/app/worker.py", line 178, in handle
  12      raise RuntimeError("database connection refused")
  13  RuntimeError: database connection refused
--
  16  2026-11-10 09:17:10,511 WARNING  [api] slow query (467 ms)
> 17  2026-11-10 09:20:01,918 ERROR    [auth] payment gateway timeout after 943 s
  18  Traceback (most recent call last):
  19    File "/srv/app/auth.py", line 296, in handle
  20      raise RuntimeError("payment gateway timeout after 943 s")
  21  RuntimeError: payment gateway timeout after 943 s
--
  25  2026-11-10 09:33:20,755 INFO     [api] request completed in 942 ms
> 26  2026-11-10 09:36:43,245 ERROR    [worker] unhandled exception in worker 158
  27  Traceback (most recent call last):
  28    File "/srv/app/worker.py", line 25, in handle
  29      raise RuntimeError("unhandled exception in worker 158")
  30  RuntimeError: unhandled exception in worker 158
--
  33  2026-11-10 09:46:56,437 DEBUG    [db] cache miss for key user:726
> 34  2026-11-10 09:50:16,116 ERROR    [db] unhandled exception in worker 107
  35  Traceback (most recent call last):
  36    File "/srv/app/db.py", line 75, in handle
  37      raise RuntimeError("unhandled exception in worker 107")
  38  RuntimeError: unhandled exception in worker 107
  39  2026-11-10 09:53:38,243 INFO     [auth] health check ok
> 40  2026-11-10 09:56:48,405 ERROR    [db] unhandled exception in worker 445
  41  Traceback (most recent call last):
```

## Notes
- Timestamps in ISO, nginx/Apache and syslog formats mark the start of an entry.
- With several files each result is labelled with its file name.
- For an overview rather than details, use `log-analyzer`.
