# free-space-alerter

## Purpose
Warn before a disk fills up. Checks one or more folders or drives against a minimum amount (or percentage) of free space and exits with 1 if any is too low, so a scheduler or script can react.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python free_space_alerter.py [PATH ...] [--min-free SIZE] [--min-percent N] [--log FILE]
```
`--min-free` takes units like `500MB` or `20GB` (default `10GB`). `--log` appends a timestamped line for every check.

## Example
```bash
python free_space_alerter.py C:/ D:/ --min-free 50GB --log space.log
```
```
LOW  C:/  42.3 GB free (9%)
OK   D:/  721.1 GB free (77%)
```

## Notes
- Exit code 0 means every disk is fine, 1 means at least one is low or unreadable.
- Pair it with cron or Windows Task Scheduler for a daily check.
- Read-only apart from the optional log file.
