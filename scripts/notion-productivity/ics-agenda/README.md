# ics-agenda

## Purpose
See your day without opening a calendar app. The tool reads any `.ics` calendar file (an export from Google Calendar, Outlook, Apple Calendar or a subscription download) and prints a clean agenda for a day or the next few days: all-day items first, then timed events with start and end, title and location. Repeating events (daily, weekly on chosen days, monthly, yearly, with counts, end dates and excluded dates) are expanded for you.

## Install
Needs the `tzdata` package so Windows has a time zone database (it does nothing harmful on Linux or macOS):
```bash
pip install -r requirements.txt
```

## Usage
```bash
python ics_agenda.py calendar.ics [--date 2026-11-16] [--days 7] [--tz Europe/London]
```
Without `--date` it shows today. Times are shown in `--tz` (UTC by default); events saved in another zone, or in UTC, are converted, and times with no zone are taken to be in the zone you chose. Cancelled events are left out. The file is only read, never changed.

## Example
```bash
python ics_agenda.py agenda.ics --date 2026-11-16 --days 3
```
```
Monday 16 Nov 2026
  09:30-09:45  Team standup  @ Zoom
  12:30-13:30  Lunch, with Alice  @ Cafe Roma
  15:00-16:00  Weekly review

Tuesday 17 Nov 2026
  09:30-09:45  Team standup  @ Zoom

Wednesday 18 Nov 2026
  09:30-09:45  Team standup  @ Zoom
  16:00        Dentist  @ Main Street Clinic

6 item(s) over 3 day(s), times in UTC.
```

## Notes
- Supported repeats: `DAILY`, `WEEKLY` (with `BYDAY`), `MONTHLY` and `YEARLY`, each with `INTERVAL`, `COUNT`, `UNTIL` and `EXDATE`. Rules like "the second Tuesday" are not expanded.
- Daylight-saving shifts in repeating events are approximate.
- Changed single occurrences of a repeating event (`RECURRENCE-ID`) are shown as originally scheduled.
- The agenda shows at most 31 days at a time.
