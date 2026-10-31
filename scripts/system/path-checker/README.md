# path-checker

## Purpose
Find the clutter in your `PATH`: folders that no longer exist, entries that are really files, blank entries and repeats. A messy PATH slows down shells and makes the wrong program run.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python path_checker.py [--path "A:B:C"] [--suggest]
```
By default it checks the real `PATH`. Pass `--path` to check any other string. `--suggest` prints a cleaned value you can paste into your shell profile. The exit code is 1 when problems are found.

## Example
```bash
python path_checker.py --suggest
```
```
#4   missing          /opt/old-tool/bin
#7   duplicate of #2  /usr/local/bin
9 entries, 2 problem(s).

Cleaned PATH:
/usr/local/bin:/usr/bin:/bin
```

## Notes
- Read-only: it never edits your environment, it only prints a suggestion.
- On Windows the comparison ignores letter case, since paths there are case-insensitive.
- `~` and environment variables inside entries are expanded before checking.
