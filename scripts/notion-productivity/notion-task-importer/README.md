# notion-task-importer

## Purpose
Turn a quick to-do list into Notion tasks. Write one task per line in a plain text file, with optional markers for the due date, tags and priority, and the tool adds each one as a new row in your Notion tasks database. Tasks whose title is already in the database are skipped, so you can run it again safely. By default it only shows what it would add.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
export NOTION_TOKEN=secret_...      # PowerShell: $env:NOTION_TOKEN = "secret_..."
python notion_task_importer.py tasks.txt --db DATABASE_ID            # show the plan
python notion_task_importer.py tasks.txt --db DATABASE_ID --apply    # create the tasks
python notion_task_importer.py tasks.txt --existing saved-query.json # plan against a saved copy
```
Task lines look like `- [ ] Write the report @2026-11-18 #work !high`. Markers: `@2026-11-18`, `@today`, `@tomorrow` or `@+3d` for the due date; `#tag` (any number); `!high`, `!medium` or `!low` for priority. `- [x]` marks a task as done; a leading `- `, `* ` or nothing at all works too. Lines starting with `# ` (hash and space) are comments.

Property names default to `Name`, `Status`, `Due`, `Tags` and `Priority`; change them with `--title-prop`, `--status-prop`, `--date-prop`, `--tags-prop` and `--priority-prop`. Status values are set with `--todo-value` and `--done-value` (for a checkbox property the box is simply ticked or not). Properties the database doesn't have are ignored and listed. Create an integration at notion.so/my-integrations and share the database with it; the token is read from the environment and never printed.

## Example
```bash
python notion_task_importer.py tasks.txt --existing notion-db.json --today 2026-11-09
```
```
5 task(s) in the file: 5 to add, 0 already in Notion.
No such property in the database (ignored): Priority
  + Write the quarterly summary  [due 2026-11-18, tags work, priority high]
  + Buy birthday present  [due 2026-11-14, tags home]
  + Send invoice to Alice  [tags work, done]
  + Call the plumber  [priority high]
  + Water the plants  [due 2026-11-11, tags home]

Dry run - nothing added. Add --apply to create these tasks in Notion.
```

## Notes
- Matching is by title, ignoring capitalisation.
- `--existing` takes the JSON returned by Notion's database query and cannot be combined with `--apply`.
- The website demo shows the plan from the sample database; real imports work on your own computer.
