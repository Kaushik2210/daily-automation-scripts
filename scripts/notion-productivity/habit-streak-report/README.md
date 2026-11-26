# habit-streak-report

## Purpose
Report on your habits from a `habit-tracker` file: current and best streaks, how consistent you
were over the last few weeks, a 14-day strip for each habit and which streaks are at risk today.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python habit_streak_report.py ~/.habits.json
python habit_streak_report.py ~/.habits.json --window 60 --habit read --habit exercise
python habit_streak_report.py ~/.habits.json --format markdown
python habit_streak_report.py habits.json --today 2026-01-08
```

The file looks like `{"habits": {"read": ["2026-01-01", "2026-01-02"], "exercise": [...]}}`, which
is what `habit-tracker` writes. Duplicate dates are counted once.

- A streak is a run of consecutive days. It stays alive until the end of today, so a habit you did
  yesterday still counts, and is flagged "at risk" until you do it.
- `--window` sets how many days the consistency percentage covers (default 30).
- Habits are ordered by current streak, then consistency.
- Formats: `text` (default), `markdown`, `json`.

## Example
`habits.json --today 2026-01-08 --window 7`

```
Habit streaks as of 2026-01-08

          streak  best  last 7d  last 14 days  note
read           3     3     71%     ------###-###-  do it today to keep the streak
meditate       1     1     14%     ------------#-  do it today to keep the streak
exercise       0     5     71%     -------#####--  broken 2 day(s) ago

Overall: 11 check-ins of 21 possible (52%) in the last 7 days.
Longest running streak: read (3 day(s)).
```

## Notes
- In the 14-day strip `#` is a day you did it and `-` is a day you didn't; the last character is today.
- Dates after `--today` are ignored.
