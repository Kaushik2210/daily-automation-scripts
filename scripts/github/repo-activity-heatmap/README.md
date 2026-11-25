# repo-activity-heatmap

## Purpose
Draw a GitHub-style contribution heatmap of a repository's commits, as text for the terminal or
as an SVG you can embed, plus a short summary: busiest day, busiest weekday and streaks.

## Install
No dependencies beyond Python 3.11+ and `git`.

## Usage
```
python repo_activity_heatmap.py
python repo_activity_heatmap.py --weeks 52 --author alice --style unicode
python repo_activity_heatmap.py --since "1 year ago" --format svg > activity.svg
python repo_activity_heatmap.py --format json
python repo_activity_heatmap.py --from-file commit-dates.txt --end 2026-11-25
```

`commit-dates.txt` holds one `YYYY-MM-DD` per line (`git log --format=%ad --date=short` makes one).
Rows are Monday to Sunday, columns are weeks, and the darkest cell is the busiest day shown.

## Example
`--from-file commit-dates.txt --end 2026-11-25 --weeks 26`

```
J    J   A    S   O   N
Mon  #+. # .  : ::. .   :. ::.
Tue  :: #::+ : :.. ::.+:::
Wed    : : #: :  +: + ++. .
Thu     . .#    :##: .:.:#:..  
Fri   . .. ::  +::. +.. ::.  . 
Sat               .#+     :    
Sun       .      ..   #        

207 commit(s) on 83 day(s), 2026-06-01 to 2026-11-25
Busiest day: 2026-10-22 (6); busiest weekday: Tue
Longest streak: 6 day(s); current streak: 0 day(s)
Less [ ][.][:][+][#] More
```

## Notes
- It reads git history only and never changes anything. Dates use each commit's author date.
- `--style unicode` draws shaded blocks; the default ASCII style works in any terminal.
- A streak counts consecutive days with commits. The current streak may end yesterday.
