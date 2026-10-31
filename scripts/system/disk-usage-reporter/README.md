# disk-usage-reporter

## Purpose
See how full your drives are at a glance, with readable sizes and a small bar for each one.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python disk_usage_reporter.py [PATH ...] [--warn PERCENT]
```
With no paths it checks every drive on Windows, or `/` and your home folder elsewhere. The exit code is 1 if any disk is at or above the `--warn` level (default 90%), which makes it handy in scheduled checks.

## Example
```bash
python disk_usage_reporter.py C:/ D:/ --warn 80
```
```
path               total      used      free  usage
C:\                475.9 GB  402.1 GB   73.8 GB  [#################---] 84%  <-- almost full
D:\                931.5 GB  210.4 GB  721.1 GB  [#####---------------] 23%
```

## Notes
- Read-only.
- Any folder works: it reports on the disk that folder lives on.
