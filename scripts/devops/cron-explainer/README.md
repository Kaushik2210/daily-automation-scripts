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
*/15 * * * *   /usr/bin/sync-data.sh
  Every 15 minutes, every day
  next: Wed 18 Nov 2026 09:45; Wed 18 Nov 2026 10:00

0 2 * * *   /usr/local/bin/backup.sh
  At 02:00, every day
  next: Thu 19 Nov 2026 02:00; Fri 20 Nov 2026 02:00

30 8 * * 1-5   /home/me/standup-reminder.sh
  At 08:30, on Monday through Friday
  next: Thu 19 Nov 2026 08:30; Fri 20 Nov 2026 08:30

0 0 1 * *   /usr/local/bin/monthly-report.sh
  At 00:00, on day 1 of the month
  next: Tue 01 Dec 2026 00:00; Fri 01 Jan 2027 00:00

0 9,17 * * MON,WED,FRI   /usr/local/bin/check-inbox.sh
  At 09:00 and 17:00, on Monday, Wednesday and Friday
  next: Wed 18 Nov 2026 17:00; Fri 20 Nov 2026 09:00

@daily   /usr/local/bin/rotate-logs.sh
  At 00:00, every day
  next: Thu 19 Nov 2026 00:00; Fri 20 Nov 2026 00:00

0 0 29 2 *   /usr/local/bin/leap-day.sh
  At 00:00, on day 29 of the month in February
  next: Tue 29 Feb 2028 00:00; Sun 29 Feb 2032 00:00
```

## Notes
- Times are shown in the machine's local time; cron itself uses the server's timezone.
- Seconds fields (6-field Quartz or Spring expressions) are not supported.
- A schedule that can never match (like 31 February) says "never".
