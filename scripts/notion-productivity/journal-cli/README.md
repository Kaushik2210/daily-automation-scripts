# journal-cli

## Purpose
Capture a thought in a few seconds. Each entry is added to a plain markdown file, grouped under a heading for the day and stamped with the time, so your journal stays readable in any editor and works with Obsidian, Notion imports or git.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python journal_cli.py TEXT... [--date YYYY-MM-DD] [--time HH:MM] [--file FILE]   # add an entry
python journal_cli.py --show DAYS [--file FILE]                                     # read recent days
python journal_cli.py --search WORD [--file FILE]                                   # find entries
```
The default file is `~/journal.md`. Without text it shows the last three days. This file is the tool's own storage, so entries are saved straight away.

## Example
```bash
python journal_cli.py --show 2 --file journal.md
```
```
2026-01-05
- 09:10 Started the day with a long walk.
- 18:45 Finished the draft and sent it out.
2026-01-06
- 08:30 Planned the week.
- 21:00 Read two chapters.
2 day(s) shown.
```

## Notes
- Days are kept in date order even if you add an entry for an earlier day.
- `--search` exits with 1 when nothing matches, which is handy in scripts.
- Anything above the first dated heading (such as your `# Journal` title) is preserved.
