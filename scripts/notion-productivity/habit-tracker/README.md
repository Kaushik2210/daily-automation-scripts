# habit-tracker

## Purpose
Keep a streak going. Check off habits each day from the terminal and see your current streak, best streak and a two-week history for each one.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python habit_tracker.py check NAME [--date YYYY-MM-DD] [--file FILE]
python habit_tracker.py uncheck NAME [--date YYYY-MM-DD]
python habit_tracker.py list
python habit_tracker.py report [--today YYYY-MM-DD]
```
Data is kept in a small JSON file (default `~/.habits.json`; choose another with `--file`). This file is the tool's own storage, so `check` writes to it straight away.

## Example
```bash
python habit_tracker.py report --file habits.json --today 2026-01-07
```
```
habit          streak  best  total  last 14 days (to 2026-01-07)
exercise            0     5      5  ..........###..
meditate            1     1      1  ............#
read                3     3      6  .........#####
```

## Notes
- A streak survives until the end of today, so checking in yesterday but not yet today still counts.
- `--today` lets you test or backfill without changing your clock.
- Checking the same day twice does nothing extra.
