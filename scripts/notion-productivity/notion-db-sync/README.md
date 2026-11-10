# notion-db-sync

## Purpose
Keep a Notion database in step with a spreadsheet. The tool reads a CSV, compares it with the rows already in a Notion database (matched on the title column, ignoring capitalisation), then adds the rows that are new and updates the cells that changed. It never deletes anything: rows that exist only in Notion are left alone. By default it only shows the plan.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
export NOTION_TOKEN=secret_...      # PowerShell: $env:NOTION_TOKEN = "secret_..."
python notion_db_sync.py tasks.csv --db DATABASE_ID            # show the plan
python notion_db_sync.py tasks.csv --db DATABASE_ID --apply    # make the changes
python notion_db_sync.py tasks.csv --existing saved-query.json # plan against a saved copy
```
Create an integration at notion.so/my-integrations, copy its token, and share the database with it (the `...` menu, then Connections). The database id is the 32-character part of its URL. The CSV's first row holds the column names, which must match the Notion property names. Supported property types are title, text, select, status, multi-select (use `;` between values), date, checkbox, number, URL, email and phone. Other columns are skipped and listed. The token is read from the environment and never printed. Writes are spaced by `--delay` seconds (Notion allows about three requests a second).

## Example
```bash
python notion_db_sync.py notion-tasks.csv --existing notion-db.json
```
```
2 to add, 1 to update, 2 in Notion not in the CSV (left alone).
  + Plan the team offsite
  + Order new keyboard
  ~ Write the weekly report: Done, Status

Dry run - nothing changed. Add --apply to write these changes to Notion.
```

## Notes
- Back up first if the database matters: see `notion-db-backup`.
- A row's key is its title; renaming a title in the CSV adds a new row rather than renaming the old one.
- `--existing` takes the JSON returned by Notion's database query, and it can never be combined with `--apply`.
- The website demo shows the plan from the sample database; real syncs work on your own computer.
