# pattern-counter

## Purpose
Answer "how often did this happen?" across a whole folder of logs. Give the tool one or more regular expressions and it counts the matching lines in every log file, including rotated `.gz` archives, and prints a table with one row per file and one column per pattern, plus totals. If a pattern has a capture group such as `timeout talking to (\w+)`, it also lists the most common captured values, so you learn not just how many timeouts there were but which servers they involved.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python pattern_counter.py LOG_OR_FOLDER [...] -p "[NAME=]REGEX" [-p ...] [-i] [-r] [--glob "*.log*"] [--top 5]
```
Name a pattern with `NAME=` so its column is readable (`-p timeouts="timeout after \d+"`); without a name the regex itself is the heading. Folders are searched for `*.log*` (which includes `app.log.1.gz`); change that with `--glob`, and add `-r` to go through sub-folders. `-i` ignores case. Each line is counted once per pattern, however many times the pattern appears in it. The exit code is 1 when nothing matched or a file couldn't be read, so it can guard scheduled jobs. The logs are only read.

## Example
```bash
python pattern_counter.py logs -p errors=ERROR -p payments=payments -p "slowest=handled request ([0-9]+)"
```
```
File            Lines  errors  payments  slowest
big.log            70       0         0        0
server-a.log       10       2         2        8
server-b.log       10       2         2        8
tiny.log            1       0         0        0
TOTAL              91       4         4       16

Top values for slowest: 0 (2), 1 (2), 2 (2), 4 (2), 5 (2)
```

## Notes
- A line counts for a pattern if the regex matches anywhere in it, so anchor patterns with `^` or `\b` to be exact.
- `.gz` files are decompressed on the fly; nothing is written to disk.
- Use `error-extractor` to read the matching entries, and `log-timeline` to see when they happened.
