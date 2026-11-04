# countdown-timer

## Purpose
See how long is left until a deadline, a holiday or the end of a short timer. Give it a date, a date with a time, or a duration such as `90s`, `25m` or `1h30m`.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python countdown_timer.py TARGET [--live] [--now 'YYYY-MM-DD HH:MM']
```
`TARGET` can be `2026-12-25`, `'2026-12-25 18:00'` or a duration (`2d 3h`, `45m`, `90s`). By default it prints the remaining time once. `--live` keeps updating every second until the time is up (Ctrl+C to stop). `--now` pretends it is another moment, which is useful for testing.

## Example
```bash
python countdown_timer.py 2026-12-25 --now '2026-11-04 09:00'
```
```
50 days, 15 hours until 2026-12-25 00:00:00
```

## Notes
- Dates without a time mean midnight at the start of that day, in your local time zone.
- A target in the past is reported as "... ago" instead of failing.
- Live mode needs a real terminal because it redraws a single line.
