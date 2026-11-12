# log-tail-filter

## Purpose
`tail -f` with a built-in filter, working the same on Windows, macOS and Linux. The tool prints the last few matching lines of a log file, then keeps watching and prints new lines as they are written, hiding everything that doesn't match. Filter by a regular expression, drop noisy lines, or show only a given level and above. It copes with log rotation: when the file is replaced by a shorter one it starts reading the new file from the top.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python log_tail_filter.py app.log -p "ERROR|timeout" [-x "healthcheck"] [-i] [--level WARNING] [-n 20]
python log_tail_filter.py app.log --level ERROR --no-follow
python log_tail_filter.py app.log -p payment --max-seconds 60
```
`-p` shows only lines matching a regex; `-x` hides lines matching one (repeat it for several); `--level WARNING` keeps WARNING, ERROR and CRITICAL; `-i` ignores case in the patterns. `-n` is how many matching lines from the end to show first (10). Following continues until you press Ctrl+C, or until `--max-seconds` or `--max-matches` is reached. With `--no-follow` it just prints the end and exits (code 1 if nothing matched). The log file is only read, never changed.

## Example
```bash
python log_tail_filter.py app.log --no-follow --level ERROR -n 3
```
```
2026-11-10 09:56:48,405 ERROR    [db] unhandled exception in worker 445
2026-11-10 10:00:11,867 ERROR    [auth] payment gateway timeout after 676 s
2026-11-10 10:22:29,059 CRITICAL [worker] out of memory, restarting worker 743
```

## Notes
- A line is shown only once it is complete, so you never see a half-written entry.
- Lines inside a stack trace have no level of their own, so a level filter hides them; use `-p` when you want traces.
- On the website demo only `--no-follow` makes sense, since the sample file never grows.
