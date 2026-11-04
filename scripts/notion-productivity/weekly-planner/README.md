# weekly-planner

## Purpose
Start each week with a clear page: a goals checklist, a section for every day with to-do lines ready to fill in, and a short review at the end. The result is plain markdown that works in any notes app, including Notion and Obsidian.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python weekly_planner.py [--week-of YYYY-MM-DD] [--goals GOAL ...] [--weekend] [--slots N]
                         [-o FILE --apply]
```
Without `--week-of` it plans the coming Monday. Any date in a week works, and the planner always starts on that week's Monday. The planner is printed; to save it, pass `-o` with `--apply` (an existing file is never overwritten).

## Example
```bash
python weekly_planner.py --week-of 2026-01-05 --goals "Finish report" "Gym 3 times"
```
```
# Week of 05 Jan 2026
*05 Jan to 09 Jan*

## Goals
- [ ] Finish report
- [ ] Gym 3 times

## Monday 05 Jan
- [ ]
- [ ]
- [ ]

## Tuesday 06 Jan
- [ ]
```

## Notes
- Wrap goals containing spaces in quotes.
- `--weekend` adds Saturday and Sunday; `--slots` changes the number of to-do lines per day.
- Paste the output into a Notion page and the checkboxes become real to-dos.
