# log-timeline

## Purpose
See when things happened. The tool groups the events in a log into time buckets (seconds, minutes, hours or days) and draws a text timeline with a bar for each bucket, a breakdown by level (`E3 W2 I10`), a marker on the busiest bucket and the empty gaps in between, so you can spot the exact minute an outage started, a quiet period when a service was down, or a traffic spike. Filter by level or a pattern to follow one kind of event.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python log_timeline.py app.log [more.log ...] [--bucket 10m] [--level ERROR] [--pattern REGEX] [--width 30] [--no-fill]
```
`--bucket` takes values like `30s`, `10m`, `1h` or `1d` (default `1h`); buckets are counted from midnight. Empty buckets are shown by default so gaps are visible (add `--no-fill` to hide them); a timeline is limited to 500 rows, so pick a bigger bucket for very long logs. It understands ISO timestamps, nginx/Apache dates and syslog dates (`--year` supplies the year for those). Lines without a timestamp, such as stack traces, are skipped and counted. The logs are only read.

## Example
```bash
python log_timeline.py app.log --bucket 30m --width 20
```
```
42 event(s) in 8 bucket(s) of 0:30:00 (28 line(s) without a timestamp skipped)
2026-11-10 08:00      3  #######               I3
2026-11-10 08:30      3  #######               I2 W1
2026-11-10 09:00      9  ####################  W5 E2 I2  <-- peak
2026-11-10 09:30      9  ####################  I5 E3 D1  <-- peak
2026-11-10 10:00      6  #############         I3 C1 E1 W1
2026-11-10 10:30      5  ###########           I3 D1 W1
2026-11-10 11:00      4  #########             I2 D1 W1
2026-11-10 11:30      3  #######               I2 W1

Letters show levels: T trace, D debug, I info, N notice, W warning, E error, C critical.
```

## Notes
- Letters: T trace, D debug, I info, N notice, W warning, E error, C critical.
- For web access logs the level breakdown is empty; the bars still show request volume over time.
- Combine with `log-analyzer` for totals and `error-extractor` for the details of a spike.
