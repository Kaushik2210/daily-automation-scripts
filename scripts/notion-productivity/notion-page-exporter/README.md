# notion-page-exporter

## Purpose
Get your Notion pages out as plain markdown files you own. The tool reads a page's blocks through the Notion API and converts them to markdown: headings, paragraphs with bold, italic, code and links, bulleted, numbered and to-do lists (including nested ones), quotes, callouts, code blocks, images, dividers and tables. Anything it can't convert is marked with a comment instead of being dropped silently.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
export NOTION_TOKEN=secret_...      # PowerShell: $env:NOTION_TOKEN = "secret_..."
python notion_page_exporter.py PAGE_ID_OR_URL [PAGE_ID_OR_URL ...]
python notion_page_exporter.py PAGE_ID --out-dir notes [--apply]
python notion_page_exporter.py --from-file saved-blocks.json --title "My page"
```
Create an integration at notion.so/my-integrations, copy its token, and share each page with it (the `...` menu, then Connections). You can paste a page's URL or its 32-character id. The markdown is printed; with `--out-dir` it lists the files it would write and `--apply` creates them (existing files are never overwritten). The token is read from the environment and never printed.

## Example
```bash
python notion_page_exporter.py --from-file notion-blocks.json --title "Project plan"
```
````
# Project plan

# Project plan

We ship on **Friday**. Details in the [spec](https://example.com/spec) and the `checklist`.

## Goals

- Launch the beta
- Collect feedback from *ten users*
1. Draft the announcement
2. Send it to the team
- [x] Book the venue
- [ ] Order snacks
> Perfect is the enemy of good.

```python
print('hello')
```

---

> Remember to back up the database.

- Sub-page: Meeting notes
````

## Notes
- Sub-pages are listed as "Sub-page: name" but not exported; run the tool again with their ids.
- Images are linked, not downloaded; Notion's own file links expire after an hour.
- `--from-file` reads the JSON returned by Notion's "retrieve block children" call.
- The website demo converts the sample blocks; exporting real pages works on your own computer.
