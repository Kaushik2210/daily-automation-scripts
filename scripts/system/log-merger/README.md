# log-merger

## Purpose
Reconstruct what happened across several machines or services. The tool merges any number of log files into one, ordered by the timestamp of each entry, so a request that passed through the web server, the API and the database reads as one story. Multi-line entries such as stack traces stay attached to the line they belong to, equal timestamps keep the order of the files you listed, and an optional label shows which file each line came from.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python log_merger.py web.log api.log db.log [--label] [--since "2026-11-10 09:05"] [--until "2026-11-10 09:30"] [--out merged.log]
```
It understands ISO timestamps (`2026-11-10 09:15:02` or `2026-11-10T09:15:02Z`), nginx/Apache dates and syslog dates (`--year` supplies the missing year). Each file is sorted on its own first, so a log with a few out-of-order lines still merges correctly (the number fixed is reported). `--since` and `--until` keep a time window. Without `--out` the merged log is printed and the summary goes to stderr; with it a new file is written and an existing file is never overwritten. The original logs are only read.

## Example
```bash
python log_merger.py logs/server-a.log logs/server-b.log --label --since "2026-11-10 09:02" --until "2026-11-10 09:06"
```
```
[server-a] 2026-11-10 09:02:00 INFO server-a handled request 2
[server-b] 2026-11-10 09:02:20 INFO server-b handled request 2
[server-a] 2026-11-10 09:03:00 ERROR server-a timeout talking to payments
[server-b] 2026-11-10 09:03:20 ERROR server-b timeout talking to payments
[server-a] 2026-11-10 09:04:00 INFO server-a handled request 4
[server-b] 2026-11-10 09:04:20 INFO server-b handled request 4
[server-a] 2026-11-10 09:05:00 INFO server-a handled request 5
[server-b] 2026-11-10 09:05:20 INFO server-b handled request 5
[server-a] 2026-11-10 09:06:00 INFO server-a handled request 6
```

## Notes
- All timestamps are compared as written, so logs from machines in different time zones should be converted to one zone first.
- Lines before the first timestamp in a file stay at the top of that file's entries.
- Feed the merged file to `log-analyzer`, `log-timeline` or `error-extractor` for a whole-system view.
