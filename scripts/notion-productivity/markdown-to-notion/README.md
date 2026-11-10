# markdown-to-notion

## Purpose
Write in markdown, publish in Notion. The tool converts a markdown file into native Notion blocks - headings, paragraphs, bold, italic, code, strikethrough and links, bulleted lists with nesting, numbered lists, to-do items, quotes, code blocks, dividers and images - and appends them to a page. By default it only shows what it would send.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
export NOTION_TOKEN=secret_...      # PowerShell: $env:NOTION_TOKEN = "secret_..."
python markdown_to_notion.py notes.md                          # show a summary
python markdown_to_notion.py notes.md --json                   # print the Notion blocks
python markdown_to_notion.py notes.md --page PAGE_ID --apply   # append to the page
```
Create an integration at notion.so/my-integrations, copy its token, and share the target page with it (the `...` menu, then Connections). `--page` accepts a page URL or its 32-character id. Blocks are added to the end of the page in batches of 100, spaced by `--delay` seconds. The tool only appends; it never edits or deletes what is already on the page. The token is read from the environment and never printed.

## Example
```bash
python markdown_to_notion.py meeting-notes.md
```
```
meeting-notes.md: 15 top-level block(s), 15 in all
  3 bulleted list item, 2 paragraph, 2 heading 2, 2 numbered list item, 2 to do, 1 heading 1, 1 quote, 1 code, 1 divider

Dry run - nothing sent. Add --page PAGE_ID --apply to append these to a page.
```

## Notes
- Consecutive lines of text are joined into one paragraph, as in standard markdown. Leave a blank line to start a new one.
- Long paragraphs are split automatically because Notion limits each text span to 2,000 characters.
- Headings deeper than `###` become Heading 3, and code languages Notion doesn't know become "plain text".
- Images are linked from their web address (`https://...`), not uploaded.
- Tables and raw HTML aren't converted and are sent as plain paragraphs.
