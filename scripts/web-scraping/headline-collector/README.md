# headline-collector

## Purpose
Skim the news without opening ten tabs. Point the tool at one or more news pages and it lists their headlines with links, skipping menu labels and duplicates. Give it a CSV file and it keeps a running archive, adding only headlines it hasn't saved before, so a daily run builds a searchable log.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python headline_collector.py SOURCE [SOURCE ...] [--levels 2-3] [--min-words 3] [--base URL] [--out headlines.csv]
```
By default it reads `<h2>` and `<h3>` headings with at least three words (the page's own title in `<h1>` and short labels like "Menu" are left out). Use `--levels 1-6` to take everything. With `--out`, new headlines are marked `*` and appended as `date, source, headline, url`.

## Example
```bash
python headline_collector.py news.html --base https://dailyexample.test/
```
```
news.html: 3 headline(s)
  - Council approves new city budget  <https://dailyexample.test/news/budget>
  - Bridge reopens after six months of repairs  <https://dailyexample.test/news/bridge>
  - Schools add coding to the curriculum  <https://dailyexample.test/news/schools>
```

## Notes
- Headlines are matched case-insensitively, so a re-capitalised repeat isn't saved twice.
- It only reads the page the server sends, so sites that load stories with JavaScript need a saved copy.
- Read the site's terms and keep to a gentle schedule. An RSS feed, if the site has one, is often the friendlier source (see `rss-digest`).
- The website demo only reads saved files; URLs work on your own computer.
