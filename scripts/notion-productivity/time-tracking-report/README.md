# time-tracking-report

## Purpose
Turn a simple CSV time log into a report of hours by project, task, day or week, with each
group's share of the total and, if you give hourly rates, the amount to bill.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python time_tracking_report.py log.csv
python time_tracking_report.py log.csv --group-by week --from 2026-11-01 --to 2026-11-30
python time_tracking_report.py log.csv --round 15 --rate 50 --rate website=80
python time_tracking_report.py log.csv --project website --format markdown
```

The log needs the columns `date` and `project`, plus either `hours` (like `1.5`) or `start` and
`end` (like `09:00` and `10:30`). A `task` column is optional. An end time earlier than the start
counts as working past midnight.

- `--round 15` rounds every entry up to the next 15 minutes.
- `--rate 50` is the default hourly rate; `--rate website=80` sets one project's rate.
- Bad rows are skipped with a note on stderr, and the rest of the report still runs.
- Formats: `text` (default), `markdown`, `json`, `csv`.

## Example
`time-log.csv --rate 60 --rate website=85`

```
hours  share      amount
website       18.50    39%    1,572.50  ########
mobile-app    17.75    38%    1,065.00  ########
admin         11.00    23%      660.00  #####
Total         47.25           3,297.50

30 entries over 10 day(s), about 4.72 h per active day.
```

## Notes
- Weeks are ISO weeks (Monday to Sunday), shown as `2026-W47`.
- Projects are sorted by hours; days and weeks are sorted by date.
