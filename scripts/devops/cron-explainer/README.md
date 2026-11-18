# cron-explainer

## Purpose
Read cron schedules without squinting at five numbers. Give the tool an expression such as `30 8 * * 1-5` or a whole crontab file and it explains each one in plain English ("At 08:30, on Monday through Friday") and lists the next times it will run, so you can check a schedule before relying on it. It understands `*`, ranges (`9-17`), lists (`1,15`), steps (`*/10`, `1-5/2`), month and weekday names (`JAN`, `MON-FRI`), Sunday as 0 or 7, and the macros `@hourly`, `@daily`, `@weekly`, `@monthly`, `@yearly` and `@reboot`.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python cron_explainer.py "*/15 9-17 * * 1-5" [more expressions] [--next 3] [--from "2026-11-18 09:30"]
python cron_explainer.py --file crontab.txt
```
Put each expression in quotes. With `--file`, comments, blank lines and `NAME=value` settings are skipped and the command is shown next to its schedule. `--from` sets the starting time for the "next runs" (default: now, in local time). If a day of the month and a weekday are both given, cron runs on days matching either one, and the explanation says so. The exit code is 1 if any expression is invalid.

## Example
```bash
python cron_explainer.py --file crontab.txt --from "2026-11-18 09:30" --next 2
```
```
{{OUTPUT}}
```

## Notes
- Times are shown in the machine's local time; cron itself uses the server's timezone.
- Seconds fields (6-field Quartz or Spring expressions) are not supported.
- A schedule that can never match (like 31 February) says "never".
