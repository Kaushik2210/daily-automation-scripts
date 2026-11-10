# notion-db-backup

## Purpose
Keep your own copy of a Notion database. The tool reads every page of a database, following Notion's paging until the end, and saves it all to one JSON file: the database definition and each page with all of its properties. It only reads - nothing in Notion is changed - and it never overwrites an existing file, so you can run it daily and keep every copy.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
export NOTION_TOKEN=secret_...      # PowerShell: $env:NOTION_TOKEN = "secret_..."
python notion_db_backup.py DATABASE_ID [--format raw|simple] [--out backup.json]
python notion_db_backup.py DATABASE_ID --stdout
python notion_db_backup.py --from-file saved-query.json --format simple --stdout
```
Create an integration at notion.so/my-integrations, copy its token, and share the database with it (the `...` menu, then Connections). The database id is the 32-character part of its URL. `--format raw` (the default) keeps exactly what Notion returns, which is best for a backup; `--format simple` writes tidy rows (title text, select names, tag lists, true/false) that are easier to read or load into other tools. Without `--out` the file is named like `notion-backup-0123abcd-20261109.json`. The token is read from the environment and never printed.

## Example
```bash
python notion_db_backup.py --from-file notion-db.json --format simple --stdout
```
```
{
  "exported_at": "2026-11-10T10:33:06",
  "database_id": "notion-db",
  "page_count": 4,
  "rows": [
    {
      "id": "00000001-aaaa-bbbb-cccc-dddddddddddd",
      "url": "https://www.notion.so/Task-1",
      "created": "2026-10-01T09:00:00.000Z",
      "edited": "2026-11-05T10:30:00.000Z",
      "properties": {
        "Name": "Write the weekly report",
        "Status": "In progress",
        "Due": "2026-11-12",
        "Tags": [
          "work"
        ],
        "Done": false,
        "Estimate": 3
      }
    },
    {
      "id": "00000002-aaaa-bbbb-cccc-dddddddddddd",
      "url": "https://www.notion.so/Task-2",
      "created": "2026-10-01T09:00:00.000Z",
      "edited": "2026-11-05T10:30:00.000Z",
      "properties": {
        "Name": "Book dentist appointment",
        "Status": "Not started",
        "Due": null,
```

## Notes
- Page contents (the blocks inside each page) are not included; use `notion-page-exporter` for those.
- The backup of a large database can be many megabytes; the summary shows the size.
- Files stored in Notion are listed by link, and those links expire after an hour.
- The `exported_at` line differs on every run, so compare backups by their pages, not the whole file.
