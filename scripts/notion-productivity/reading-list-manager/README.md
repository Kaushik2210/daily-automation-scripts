# reading-list-manager

## Purpose
Keep track of what you want to read, what you're reading and what you finished. Add books, move them through the statuses (to-read, reading, done), give finished ones a 1-5 rating, and see a summary of how much you read and what you liked best. Everything lives in one small JSON file you can back up or sync.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python reading_list_manager.py add "Deep Work" --author "Cal Newport"
python reading_list_manager.py list [--status to-read|reading|done]
python reading_list_manager.py start 3
python reading_list_manager.py finish 3 --rating 5
python reading_list_manager.py rate 3 --rating 4
python reading_list_manager.py remove 3
python reading_list_manager.py stats
```
`start`, `finish`, `rate` and `remove` take one or more book numbers (shown by `list`). The list is kept in `~/.reading-list.json`; point to another file with `--file`. `list` and `stats` only read it. Adding a title that is already there is refused.

## Example
```bash
python reading_list_manager.py list --file reading-list.json
```
```
READING (1)
    2  The Pragmatic Programmer - Hunt & Thomas

TO-READ (2)
    3  Atomic Habits - James Clear
    4  Staff Engineer - Will Larson

DONE (2)
    1  Deep Work - Cal Newport  [5/5]
    5  Thinking, Fast and Slow - Daniel Kahneman  [4/5]
```

## Notes
- `finish` records today's date, so `stats` can show how many books you finished each month.
- `--today` only exists so examples and tests give the same answer every time.
- Remove asks no questions; keep a copy of the JSON file if the list matters.
- Pair it with `notion-db-sync` to mirror the list in Notion.
