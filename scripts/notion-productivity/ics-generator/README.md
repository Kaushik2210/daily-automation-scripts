# ics-generator

## Purpose
Put a list of events into any calendar app in one step. The tool reads a CSV (title, start, optional end, location and description) and writes a standard `.ics` file that Google Calendar, Outlook, Apple Calendar and most phone calendars can import. It handles timed events, all-day events, time zones, reminders and the awkward escaping and line-folding rules of the iCalendar format.

## Install
Needs the `tzdata` package so Windows has a time zone database (it does nothing harmful on Linux or macOS):
```bash
pip install -r requirements.txt
```

## Usage
```bash
python ics_generator.py events.csv [--out events.ics] [--tz Europe/London] [--utc] [--minutes 60] [--alarm 15]
```
CSV columns (a header row is required): `title`, `start`, and optionally `end`, `location`, `description`. The names `summary`, `name`, `begin`, `date`, `finish`, `place`, `notes` and `details` work too. Write times as `2026-11-16 09:30` and all-day events as just `2026-11-16`. A missing end becomes `--minutes` later (60 by default) or the next day for all-day events. With `--tz` the times carry that zone; add `--utc` to convert them to UTC, the most widely compatible choice. Without either they are "floating" local times. `--alarm 15` adds a reminder 15 minutes before each timed event. The result is printed, or saved with `--out` (an existing file is never overwritten). To import, open the file in your calendar app or use its Import option.

## Example
```bash
python ics_generator.py events.csv --tz Europe/London --utc --alarm 10 --stamp 2026-11-01T08:00
```
```
BEGIN:VCALENDAR

VERSION:2.0

PRODID:-//daily-automation-scripts//ics-generator//EN

CALSCALE:GREGORIAN

X-WR-CALNAME:Events

BEGIN:VEVENT

UID:cae0c59315b3230a4541@daily-automation-scripts

DTSTAMP:20261101T080000Z

DTSTART:20261116T093000Z

DTEND:20261116T094500Z

SUMMARY:Team standup

LOCATION:Zoom

DESCRIPTION:Daily sync

BEGIN:VALARM

ACTION:DISPLAY

```

## Notes
- Rows that can't be converted (no title, bad date, end before start) are skipped with a message, and the exit code is 1.
- Each event gets a stable ID built from its title and start, so importing the same file twice updates events instead of duplicating them in most calendars.
- `--stamp` only exists so examples and tests give the same output every time.
