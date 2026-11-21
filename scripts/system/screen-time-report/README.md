# screen-time-report

## Purpose
See where your computer time goes. The tool reads the log written by `active-window-logger` and adds up how long each application had focus, per day, with a share of the day and a small bar. Each log row lasts until the next one; a long gap (more than `--idle-gap` minutes, 5 by default) is treated as you being away and counted only up to that limit, and lock screens are never counted. Useful for timesheets, focus reviews or just curiosity.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python screen_time_report.py window-log.csv [--date 2026-11-20] [--top 8] [--idle-gap 5] [--by-title] [--ignore Spotify,Slack]
```
The input is a CSV with the columns `time,app,title` (ISO times). `--date` limits the report to one day, `--top` limits how many applications are listed per day, `--by-title` splits applications by window title (to see which documents or sites took the time) and `--ignore` leaves out applications. With several days in the log a combined total is added. The exit code is 1 when there is no usage to report.

## Example
```bash
python screen_time_report.py window-log.csv --date 2026-11-20 --idle-gap 30
```
```
2026-11-20  total 4h 51m
  Code                                3h 30m   72%  ##################
  Chrome                                 53m   18%  #####
  Slack                                  18m    6%  ##
  Terminal                                6m    2%  #
  Spotify                                 4m    1%  #

Based on 23 log row(s) covering 27h 00m; gaps over 30 min and lock screens count as idle.
```

## Notes
- A larger `--idle-gap` counts more of the quiet periods as use; a smaller one is stricter. Pick the value that matches how you work.
- The last row of a log has no end time, so it adds nothing until a newer row follows it.
- Pair it with `active-window-logger` to produce the log.
