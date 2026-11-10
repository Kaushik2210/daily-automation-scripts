# weekly-review

## Purpose
Start your weekly review with the facts already filled in. The tool builds a markdown review for any week from the files your other tools keep: the highlights from your journal, a habit grid for Monday to Sunday, finished and open to-dos (most urgent first), and the notes you captured. It ends with reflection questions and three empty slots for next week's priorities, ready to paste into Notion, Obsidian or any note app.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python weekly_review.py [--week-of 2026-01-07] [--journal journal.md] [--habits habits.json]
                        [--todos todos.json] [--notes notes.json] [--out review.md]
```
Every input is optional; sections are included only for the files you give. `--week-of` takes any date and reviews the Monday-to-Sunday week it falls in (default: this week). The files are the ones written by `journal-cli` (markdown with `## YYYY-MM-DD` days), `habit-tracker`, `todo-cli` and `quick-notes`. They are only read, never changed. The result is printed, or saved to a new file with `--out` (an existing file is never overwritten).

## Example
```bash
python weekly_review.py --week-of 2026-01-07 --journal journal.md --habits habits.json --todos todos.json --notes notes.json
```
```
# Weekly review: 05 Jan - 11 Jan 2026

## From my journal
**Monday 05 Jan**
- 09:10 Started the day with a long walk.
- 18:45 Finished the draft and sent it out.

**Tuesday 06 Jan**
- 08:30 Planned the week.
- 21:00 Read two chapters.

## Habits

| Habit | Mo | Tu | We | Th | Fr | Sa | Su | Total |
|---|---|---|---|---|---|---|---|---|
| read | x | x | x | - | - | - | - | 3/7 |
| exercise | x | x | - | - | - | - | - | 2/7 |
| meditate | - | - | x | - | - | - | - | 1/7 |

## To-dos

Finished: 1 - still open: 3

- [x] Reply to Sam
- [ ] Write the weekly report (high)
- [ ] Renew passport (high)
- [ ] Book dentist appointment (normal)

## Notes I captured
- Mon 05 Jan: Buy oat milk #errands
```

## Notes
- The to-do file has no dates, so it shows the current state of your list rather than what changed that week.
- Journal entries are matched by the date in each `## YYYY-MM-DD` heading.
- Reflection prompts are in the `PROMPTS` list at the top of the script if you'd like different questions.
