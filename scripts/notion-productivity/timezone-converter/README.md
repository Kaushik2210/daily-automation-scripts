# timezone-converter

## Purpose
Work out what time a meeting is for everyone. Give a time in one zone and see it in several others, including whether it lands on the next or previous day. Daylight saving changes are handled for the date you choose.

## Install
Needs the `tzdata` package so Windows has a time zone database (it does nothing harmful on Linux or macOS):
```bash
pip install -r requirements.txt
```

## Usage
```bash
python timezone_converter.py TIME [--from ZONE] [--to ZONE ...] [--date YYYY-MM-DD]
python timezone_converter.py --find london
```
`TIME` can be `14:30` or `2:30pm`. Zone names look like `Europe/London` or `America/New_York`. `--find` searches the zone names.

## Example
```bash
python timezone_converter.py 12:00 --from Europe/London --to America/New_York Asia/Tokyo --date 2026-01-15
```
```
Thu 2026-01-15 12:00 Europe/London (+0000)
  Thu 2026-01-15 07:00  America/New_York (-0500)
  Thu 2026-01-15 21:00  Asia/Tokyo (+0900)
  Thu 2026-01-15 17:30  Asia/Kolkata (+0530)
```

## Notes
- The date matters: the same clock time converts differently in summer and winter.
- Unknown zone names stop with a message that suggests `--find`.
- Read-only.
