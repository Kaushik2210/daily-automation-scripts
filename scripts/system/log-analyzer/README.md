# log-analyzer

## Purpose
Understand a log file in seconds instead of scrolling through thousands of lines. The tool reads one or more logs and reports how many entries there are and over what time span, how they split across levels (DEBUG, INFO, WARNING, ERROR, CRITICAL), which hours were busiest, and which errors repeat most, grouped so that "timeout after 30 s" and "timeout after 45 s" count as the same problem. Stack traces and other continuation lines are attached to the entry above them instead of being counted as separate entries.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python log_analyzer.py app.log [more.log ...] [--top 5] [--year 2026]
```
It understands ISO timestamps (`2026-11-10 09:15:02,123` or `2026-11-10T09:15:02Z`), nginx/Apache dates (`[10/Nov/2026:09:15:02 +0000]`) and syslog dates (`Nov 10 09:15:02`, where `--year` supplies the missing year). Levels are recognised anywhere in the line, case-insensitively; `WARN` counts as WARNING, `ERR` as ERROR and `FATAL` as CRITICAL. The file is only read.

## Example
```bash
python log_analyzer.py app.log --top 3
```
```
42 entries from 2026-11-10 08:00:23 to 2026-11-10 11:51:35
28 continuation line(s) such as stack traces were attached to the entry above them.

Levels:
  DEBUG          3    7.1%  ###
  INFO          22   52.4%  ########################
  WARNING       10   23.8%  ###########
  ERROR          6   14.3%  #######
  CRITICAL       1    2.4%  #

Busiest hours (top 3):
  2026-11-10 09:00      18  ########################
  2026-11-10 10:00      11  ###############
  2026-11-10 11:00       7  #########

Most common errors (top 3):
      3x  unhandled exception in worker #
      2x  payment gateway timeout after # s
      1x  database connection refused
```

## Notes
- Lines before the first timestamped line are counted as stray and ignored.
- Lines with a timestamp but no level (such as web access logs) are counted under `(none)`; use `status-code-counter` for those.
- Big logs are read into memory, which is fine up to a few hundred megabytes.
