# system-info-report

## Purpose
Get the basics of a machine in one command: OS, CPU count, memory, disk, Python version and where it runs from. Useful for bug reports and for checking a server or a fresh laptop.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python system_info_report.py [--json]
```

## Example
```bash
python system_info_report.py
```
```
hostname       DESKTOP-4F2K
user           kaushik
os             Windows 11
architecture   AMD64
cpu count      12
memory gb      15.7
disk total gb  475.9
disk free gb   73.8
python         3.13.7
```

## Notes
- Memory shows `n/a` on Windows because the standard library has no portable way to read it.
- `--json` is handy for logging or sending the report to another tool.
- Read-only. Nothing sensitive is collected beyond the host and user name.
