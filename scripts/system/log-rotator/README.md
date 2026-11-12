# log-rotator

## Purpose
Stop log files from growing forever without needing `logrotate` (which isn't available on Windows). Point the tool at log files or folders of logs; any file over your size limit is compressed into `name.log.1.gz`, older archives shift up (`.1.gz` becomes `.2.gz`) and archives beyond your `--keep` limit are deleted. The compressed copy is read back and checked before the original is touched. By default it only shows what it would do.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python log_rotator.py LOG_OR_FOLDER [...] --max-size 10MB [--keep 5] [--pattern "*.log"] [--rename] [--apply]
```
Sizes can be written as `500KB`, `10MB` or `2G`. Folders are searched (not recursively) for files matching `--pattern`. By default the original log is emptied in place (so a running program keeps writing to the same file) and any lines written while it was being archived are preserved. With `--rename` the original is removed instead, which is better for programs that reopen their log after rotation; if the file grows during the copy, the rotation stops and you can run it again. Run it daily from cron or Task Scheduler.

## Example
```bash
python log_rotator.py logs --max-size 2KB --keep 3
```
```
4 log file(s), 1 at least 2.0 KB.
  rotate  big.log  (5.0 KB) -> big.log.1.gz, original emptied in place
  skip    server-a.log  (542 B)
  skip    server-b.log  (542 B)
  skip    tiny.log  (33 B)

Dry run - nothing changed. Add --apply to rotate.
```

## Notes
- Add `--apply` to rotate. Without it nothing is changed.
- Emptying a log in place can lose a line or two for programs that don't open their log in append mode; use `--rename` if that matters.
- Archives are standard gzip, readable with `gunzip`, 7-Zip or `log-analyzer` after unzipping.
- On the website demo the rotation happens in your browser's temporary folder.
