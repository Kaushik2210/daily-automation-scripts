# daily-automation-scripts

[![CI](https://github.com/Kaushik2210/daily-automation-scripts/actions/workflows/ci.yml/badge.svg)](https://github.com/Kaushik2210/daily-automation-scripts/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Platforms](https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/lint-ruff-261230)](https://docs.astral.sh/ruff/)

A 30-day challenge: ten small, useful automation scripts every day, 300 in total. Each script lives in its own folder, comes with a README and tests, and lands as its own commit and push.

## Try it in your browser
**[kaushik2210.github.io/daily-automation-scripts](https://kaushik2210.github.io/daily-automation-scripts/)** has a page for every tool. Open one, add some files (or hit the sample files button) and the real Python script runs right in your browser. Nothing is uploaded anywhere. Tools that need the network or your computer (email, port scanning and so on) say so and show the command to run locally.

Prefer your own machine? Start the local dashboard, which runs the scripts for real and can read your actual folders:

```bash
python web/dashboard.py
```

## The challenge
- 30 days, 10 scripts a day. The full list is in [PLAN.md](PLAN.md).
- Easy scripts first (days 1-10), medium next (11-20), more advanced to finish (21-30).
- Python 3.11+ with the standard library wherever possible. Extra packages go in a per-script `requirements.txt`.
- Rules for writing scripts are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Running a script
Every script is a command-line tool with `--help`:

```bash
python scripts/<category>/<script-name>/<script_name>.py --help
```

If the script folder has a `requirements.txt`, install it first with `pip install -r requirements.txt`. Anything that changes files runs as a dry run unless you pass `--apply`. Tokens are always read from environment variables, never from the code.

## Development
```bash
pip install ruff pytest
make check        # ruff + pytest
make index        # rebuild the index below
```

A [pre-commit](https://pre-commit.com) config is included (`pre-commit install`).

CI lints and runs the tests on Linux (Python 3.11 and 3.12) for every push. Windows and macOS are tested on pull requests, every Monday and on demand from the Actions tab, because those runners use many times more Actions minutes.

## Categories
`files`, `pdf-docs`, `github`, `email`, `web-scraping`, `notion-productivity`, `data`, `system`, `security`, `media`, `text`, `devops`

## Index
The table below is rebuilt by `python tools/update_index.py` from `PLAN.md` and the script folders. Don't edit between the markers by hand.

<!-- INDEX:START -->

**Progress: 152/300 done**

| Day | # | Script | Category | Source | Live |
| --- | --- | --- | --- | --- | --- |
| 01 | 01 | bulk-file-renamer | files | [bulk-file-renamer](scripts/files/bulk-file-renamer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/bulk-file-renamer/) |
| 01 | 02 | duplicate-file-finder | files | [duplicate-file-finder](scripts/files/duplicate-file-finder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/duplicate-file-finder/) |
| 01 | 03 | folder-organizer | files | [folder-organizer](scripts/files/folder-organizer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/folder-organizer/) |
| 01 | 04 | empty-folder-cleaner | files | [empty-folder-cleaner](scripts/files/empty-folder-cleaner/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/empty-folder-cleaner/) |
| 01 | 05 | file-size-lister | files | [file-size-lister](scripts/files/file-size-lister/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/file-size-lister/) |
| 01 | 06 | old-file-finder | files | [old-file-finder](scripts/files/old-file-finder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/old-file-finder/) |
| 01 | 07 | downloads-sorter | files | [downloads-sorter](scripts/files/downloads-sorter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/downloads-sorter/) |
| 01 | 08 | extension-counter | files | [extension-counter](scripts/files/extension-counter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/extension-counter/) |
| 01 | 09 | filename-normalizer | files | [filename-normalizer](scripts/files/filename-normalizer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/filename-normalizer/) |
| 01 | 10 | tree-printer | files | [tree-printer](scripts/files/tree-printer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/tree-printer/) |
| 02 | 01 | word-counter | text | [word-counter](scripts/text/word-counter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/word-counter/) |
| 02 | 02 | line-deduper | text | [line-deduper](scripts/text/line-deduper/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/line-deduper/) |
| 02 | 03 | case-converter | text | [case-converter](scripts/text/case-converter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/case-converter/) |
| 02 | 04 | markdown-toc-generator | text | [markdown-toc-generator](scripts/text/markdown-toc-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/markdown-toc-generator/) |
| 02 | 05 | whitespace-stripper | text | [whitespace-stripper](scripts/text/whitespace-stripper/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/whitespace-stripper/) |
| 02 | 06 | bulk-find-replace | text | [bulk-find-replace](scripts/text/bulk-find-replace/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/bulk-find-replace/) |
| 02 | 07 | text-diff-viewer | text | [text-diff-viewer](scripts/text/text-diff-viewer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/text-diff-viewer/) |
| 02 | 08 | lorem-generator | text | [lorem-generator](scripts/text/lorem-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/lorem-generator/) |
| 02 | 09 | slugify-text | text | [slugify-text](scripts/text/slugify-text/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/slugify-text/) |
| 02 | 10 | csv-to-markdown | data | [csv-to-markdown](scripts/data/csv-to-markdown/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/csv-to-markdown/) |
| 03 | 01 | disk-usage-reporter | system | [disk-usage-reporter](scripts/system/disk-usage-reporter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/disk-usage-reporter/) |
| 03 | 02 | system-info-report | system | [system-info-report](scripts/system/system-info-report/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/system-info-report/) |
| 03 | 03 | large-file-finder | system | [large-file-finder](scripts/system/large-file-finder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/large-file-finder/) |
| 03 | 04 | temp-cleaner | system | [temp-cleaner](scripts/system/temp-cleaner/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/temp-cleaner/) |
| 03 | 05 | env-var-lister | system | [env-var-lister](scripts/system/env-var-lister/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/env-var-lister/) |
| 03 | 06 | path-checker | system | [path-checker](scripts/system/path-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/path-checker/) |
| 03 | 07 | python-env-reporter | system | [python-env-reporter](scripts/system/python-env-reporter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/python-env-reporter/) |
| 03 | 08 | free-space-alerter | system | [free-space-alerter](scripts/system/free-space-alerter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/free-space-alerter/) |
| 03 | 09 | folder-size-history | system | [folder-size-history](scripts/system/folder-size-history/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/folder-size-history/) |
| 03 | 10 | hosts-file-viewer | system | [hosts-file-viewer](scripts/system/hosts-file-viewer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/hosts-file-viewer/) |
| 04 | 01 | csv-cleaner | data | [csv-cleaner](scripts/data/csv-cleaner/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/csv-cleaner/) |
| 04 | 02 | csv-column-stats | data | [csv-column-stats](scripts/data/csv-column-stats/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/csv-column-stats/) |
| 04 | 03 | json-pretty-printer | data | [json-pretty-printer](scripts/data/json-pretty-printer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/json-pretty-printer/) |
| 04 | 04 | json-yaml-converter | data | [json-yaml-converter](scripts/data/json-yaml-converter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/json-yaml-converter/) |
| 04 | 05 | csv-to-json | data | [csv-to-json](scripts/data/csv-to-json/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/csv-to-json/) |
| 04 | 06 | json-to-csv | data | [json-to-csv](scripts/data/json-to-csv/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/json-to-csv/) |
| 04 | 07 | csv-merger | data | [csv-merger](scripts/data/csv-merger/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/csv-merger/) |
| 04 | 08 | csv-splitter | data | [csv-splitter](scripts/data/csv-splitter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/csv-splitter/) |
| 04 | 09 | csv-deduper | data | [csv-deduper](scripts/data/csv-deduper/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/csv-deduper/) |
| 04 | 10 | excel-to-csv | data | [excel-to-csv](scripts/data/excel-to-csv/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/excel-to-csv/) |
| 05 | 01 | password-strength-checker | security | [password-strength-checker](scripts/security/password-strength-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/password-strength-checker/) |
| 05 | 02 | password-generator | security | [password-generator](scripts/security/password-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/password-generator/) |
| 05 | 03 | hash-checker | security | [hash-checker](scripts/security/hash-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/hash-checker/) |
| 05 | 04 | file-hasher | security | [file-hasher](scripts/security/file-hasher/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/file-hasher/) |
| 05 | 05 | checksum-manifest | security | [checksum-manifest](scripts/security/checksum-manifest/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/checksum-manifest/) |
| 05 | 06 | secret-scanner | security | [secret-scanner](scripts/security/secret-scanner/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/secret-scanner/) |
| 05 | 07 | env-file-auditor | security | [env-file-auditor](scripts/security/env-file-auditor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/env-file-auditor/) |
| 05 | 08 | token-generator | security | [token-generator](scripts/security/token-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/token-generator/) |
| 05 | 09 | base64-tool | security | [base64-tool](scripts/security/base64-tool/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/base64-tool/) |
| 05 | 10 | permission-auditor | security | [permission-auditor](scripts/security/permission-auditor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/permission-auditor/) |
| 06 | 01 | image-resizer | media | [image-resizer](scripts/media/image-resizer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/image-resizer/) |
| 06 | 02 | image-converter | media | [image-converter](scripts/media/image-converter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/image-converter/) |
| 06 | 03 | image-metadata-reader | media | [image-metadata-reader](scripts/media/image-metadata-reader/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/image-metadata-reader/) |
| 06 | 04 | screenshot-organizer | media | [screenshot-organizer](scripts/media/screenshot-organizer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/screenshot-organizer/) |
| 06 | 05 | thumbnail-generator | media | [thumbnail-generator](scripts/media/thumbnail-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/thumbnail-generator/) |
| 06 | 06 | image-rotator | media | [image-rotator](scripts/media/image-rotator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/image-rotator/) |
| 06 | 07 | qr-generator | media | [qr-generator](scripts/media/qr-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/qr-generator/) |
| 06 | 08 | grayscale-converter | media | [grayscale-converter](scripts/media/grayscale-converter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/grayscale-converter/) |
| 06 | 09 | photo-date-renamer | media | [photo-date-renamer](scripts/media/photo-date-renamer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/photo-date-renamer/) |
| 06 | 10 | gif-frame-extractor | media | [gif-frame-extractor](scripts/media/gif-frame-extractor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/gif-frame-extractor/) |
| 07 | 01 | habit-tracker | notion-productivity | [habit-tracker](scripts/notion-productivity/habit-tracker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/habit-tracker/) |
| 07 | 02 | pomodoro-timer | notion-productivity | [pomodoro-timer](scripts/notion-productivity/pomodoro-timer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/pomodoro-timer/) |
| 07 | 03 | todo-cli | notion-productivity | [todo-cli](scripts/notion-productivity/todo-cli/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/todo-cli/) |
| 07 | 04 | journal-cli | notion-productivity | [journal-cli](scripts/notion-productivity/journal-cli/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/journal-cli/) |
| 07 | 05 | countdown-timer | notion-productivity | [countdown-timer](scripts/notion-productivity/countdown-timer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/countdown-timer/) |
| 07 | 06 | timezone-converter | notion-productivity | [timezone-converter](scripts/notion-productivity/timezone-converter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/timezone-converter/) |
| 07 | 07 | quick-notes | notion-productivity | [quick-notes](scripts/notion-productivity/quick-notes/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/quick-notes/) |
| 07 | 08 | expense-logger | notion-productivity | [expense-logger](scripts/notion-productivity/expense-logger/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/expense-logger/) |
| 07 | 09 | break-reminder | notion-productivity | [break-reminder](scripts/notion-productivity/break-reminder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/break-reminder/) |
| 07 | 10 | weekly-planner | notion-productivity | [weekly-planner](scripts/notion-productivity/weekly-planner/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/weekly-planner/) |
| 08 | 01 | standup-generator | github | [standup-generator](scripts/github/standup-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/standup-generator/) |
| 08 | 02 | git-log-summarizer | github | [git-log-summarizer](scripts/github/git-log-summarizer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/git-log-summarizer/) |
| 08 | 03 | commit-message-linter | github | [commit-message-linter](scripts/github/commit-message-linter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/commit-message-linter/) |
| 08 | 04 | git-author-stats | github | [git-author-stats](scripts/github/git-author-stats/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/git-author-stats/) |
| 08 | 05 | todo-comment-finder | github | [todo-comment-finder](scripts/github/todo-comment-finder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/todo-comment-finder/) |
| 08 | 06 | gitignore-generator | github | [gitignore-generator](scripts/github/gitignore-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/gitignore-generator/) |
| 08 | 07 | repo-readme-generator | github | [repo-readme-generator](scripts/github/repo-readme-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/repo-readme-generator/) |
| 08 | 08 | changelog-generator | github | [changelog-generator](scripts/github/changelog-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/changelog-generator/) |
| 08 | 09 | branch-lister | github | [branch-lister](scripts/github/branch-lister/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/branch-lister/) |
| 08 | 10 | repo-size-reporter | github | [repo-size-reporter](scripts/github/repo-size-reporter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/repo-size-reporter/) |
| 09 | 01 | pdf-merger | pdf-docs | [pdf-merger](scripts/pdf-docs/pdf-merger/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/pdf-docs/pdf-merger/) |
| 09 | 02 | pdf-splitter | pdf-docs | [pdf-splitter](scripts/pdf-docs/pdf-splitter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/pdf-docs/pdf-splitter/) |
| 09 | 03 | pdf-page-counter | pdf-docs | [pdf-page-counter](scripts/pdf-docs/pdf-page-counter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/pdf-docs/pdf-page-counter/) |
| 09 | 04 | pdf-text-extractor | pdf-docs | [pdf-text-extractor](scripts/pdf-docs/pdf-text-extractor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/pdf-docs/pdf-text-extractor/) |
| 09 | 05 | pdf-rotator | pdf-docs | [pdf-rotator](scripts/pdf-docs/pdf-rotator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/pdf-docs/pdf-rotator/) |
| 09 | 06 | markdown-to-pdf | pdf-docs | [markdown-to-pdf](scripts/pdf-docs/markdown-to-pdf/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/pdf-docs/markdown-to-pdf/) |
| 09 | 07 | invoice-renamer | pdf-docs | [invoice-renamer](scripts/pdf-docs/invoice-renamer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/pdf-docs/invoice-renamer/) |
| 09 | 08 | pdf-metadata-viewer | pdf-docs | [pdf-metadata-viewer](scripts/pdf-docs/pdf-metadata-viewer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/pdf-docs/pdf-metadata-viewer/) |
| 09 | 09 | docx-text-extractor | pdf-docs | [docx-text-extractor](scripts/pdf-docs/docx-text-extractor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/pdf-docs/docx-text-extractor/) |
| 09 | 10 | images-to-pdf | pdf-docs | [images-to-pdf](scripts/pdf-docs/images-to-pdf/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/pdf-docs/images-to-pdf/) |
| 10 | 01 | bulk-url-checker | web-scraping | [bulk-url-checker](scripts/web-scraping/bulk-url-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/bulk-url-checker/) |
| 10 | 02 | link-extractor | web-scraping | [link-extractor](scripts/web-scraping/link-extractor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/link-extractor/) |
| 10 | 03 | robots-checker | web-scraping | [robots-checker](scripts/web-scraping/robots-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/robots-checker/) |
| 10 | 04 | rss-digest | web-scraping | [rss-digest](scripts/web-scraping/rss-digest/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/rss-digest/) |
| 10 | 05 | header-inspector | web-scraping | [header-inspector](scripts/web-scraping/header-inspector/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/header-inspector/) |
| 10 | 06 | page-title-fetcher | web-scraping | [page-title-fetcher](scripts/web-scraping/page-title-fetcher/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/page-title-fetcher/) |
| 10 | 07 | broken-link-finder | web-scraping | [broken-link-finder](scripts/web-scraping/broken-link-finder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/broken-link-finder/) |
| 10 | 08 | sitemap-lister | web-scraping | [sitemap-lister](scripts/web-scraping/sitemap-lister/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/sitemap-lister/) |
| 10 | 09 | url-expander | web-scraping | [url-expander](scripts/web-scraping/url-expander/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/url-expander/) |
| 10 | 10 | ping-checker | system | [ping-checker](scripts/system/ping-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/ping-checker/) |
| 11 | 01 | web-scraper | web-scraping | [web-scraper](scripts/web-scraping/web-scraper/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/web-scraper/) |
| 11 | 02 | price-tracker | web-scraping | [price-tracker](scripts/web-scraping/price-tracker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/price-tracker/) |
| 11 | 03 | html-table-extractor | web-scraping | [html-table-extractor](scripts/web-scraping/html-table-extractor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/html-table-extractor/) |
| 11 | 04 | page-change-detector | web-scraping | [page-change-detector](scripts/web-scraping/page-change-detector/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/page-change-detector/) |
| 11 | 05 | meta-tag-auditor | web-scraping | [meta-tag-auditor](scripts/web-scraping/meta-tag-auditor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/meta-tag-auditor/) |
| 11 | 06 | image-downloader | web-scraping | [image-downloader](scripts/web-scraping/image-downloader/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/image-downloader/) |
| 11 | 07 | headline-collector | web-scraping | [headline-collector](scripts/web-scraping/headline-collector/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/headline-collector/) |
| 11 | 08 | wayback-checker | web-scraping | [wayback-checker](scripts/web-scraping/wayback-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/wayback-checker/) |
| 11 | 09 | page-text-extractor | web-scraping | [page-text-extractor](scripts/web-scraping/page-text-extractor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/page-text-extractor/) |
| 11 | 10 | job-listing-watcher | web-scraping | [job-listing-watcher](scripts/web-scraping/job-listing-watcher/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/job-listing-watcher/) |
| 12 | 01 | email-digest | email | [email-digest](scripts/email/email-digest/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/email/email-digest/) |
| 12 | 02 | unsubscribe-finder | email | [unsubscribe-finder](scripts/email/unsubscribe-finder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/email/unsubscribe-finder/) |
| 12 | 03 | attachment-lister | email | [attachment-lister](scripts/email/attachment-lister/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/email/attachment-lister/) |
| 12 | 04 | sender-stats | email | [sender-stats](scripts/email/sender-stats/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/email/sender-stats/) |
| 12 | 05 | subject-search | email | [subject-search](scripts/email/subject-search/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/email/subject-search/) |
| 12 | 06 | mailbox-size-reporter | email | [mailbox-size-reporter](scripts/email/mailbox-size-reporter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/email/mailbox-size-reporter/) |
| 12 | 07 | eml-to-text | email | [eml-to-text](scripts/email/eml-to-text/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/email/eml-to-text/) |
| 12 | 08 | email-validator | email | [email-validator](scripts/email/email-validator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/email/email-validator/) |
| 12 | 09 | header-analyzer | email | [header-analyzer](scripts/email/header-analyzer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/email/header-analyzer/) |
| 12 | 10 | mbox-splitter | email | [mbox-splitter](scripts/email/mbox-splitter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/email/mbox-splitter/) |
| 13 | 01 | github-stats-reporter | github | [github-stats-reporter](scripts/github/github-stats-reporter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/github-stats-reporter/) |
| 13 | 02 | stale-branch-cleaner | github | [stale-branch-cleaner](scripts/github/stale-branch-cleaner/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/stale-branch-cleaner/) |
| 13 | 03 | issue-exporter | github | [issue-exporter](scripts/github/issue-exporter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/issue-exporter/) |
| 13 | 04 | pr-review-queue | github | [pr-review-queue](scripts/github/pr-review-queue/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/pr-review-queue/) |
| 13 | 05 | star-tracker | github | [star-tracker](scripts/github/star-tracker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/star-tracker/) |
| 13 | 06 | language-breakdown | github | [language-breakdown](scripts/github/language-breakdown/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/language-breakdown/) |
| 13 | 07 | release-notifier | github | [release-notifier](scripts/github/release-notifier/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/release-notifier/) |
| 13 | 08 | contributor-leaderboard | github | [contributor-leaderboard](scripts/github/contributor-leaderboard/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/contributor-leaderboard/) |
| 13 | 09 | rate-limit-checker | github | [rate-limit-checker](scripts/github/rate-limit-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/rate-limit-checker/) |
| 13 | 10 | label-auditor | github | [label-auditor](scripts/github/label-auditor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/label-auditor/) |
| 14 | 01 | notion-db-sync | notion-productivity | [notion-db-sync](scripts/notion-productivity/notion-db-sync/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/notion-db-sync/) |
| 14 | 02 | notion-page-exporter | notion-productivity | [notion-page-exporter](scripts/notion-productivity/notion-page-exporter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/notion-page-exporter/) |
| 14 | 03 | notion-task-importer | notion-productivity | [notion-task-importer](scripts/notion-productivity/notion-task-importer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/notion-task-importer/) |
| 14 | 04 | markdown-to-notion | notion-productivity | [markdown-to-notion](scripts/notion-productivity/markdown-to-notion/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/markdown-to-notion/) |
| 14 | 05 | notion-db-backup | notion-productivity | [notion-db-backup](scripts/notion-productivity/notion-db-backup/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/notion-db-backup/) |
| 14 | 06 | ics-generator | notion-productivity | [ics-generator](scripts/notion-productivity/ics-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/ics-generator/) |
| 14 | 07 | ics-agenda | notion-productivity | [ics-agenda](scripts/notion-productivity/ics-agenda/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/ics-agenda/) |
| 14 | 08 | weekly-review | notion-productivity | [weekly-review](scripts/notion-productivity/weekly-review/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/weekly-review/) |
| 14 | 09 | reading-list-manager | notion-productivity | [reading-list-manager](scripts/notion-productivity/reading-list-manager/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/reading-list-manager/) |
| 14 | 10 | bookmark-deduper | notion-productivity | [bookmark-deduper](scripts/notion-productivity/bookmark-deduper/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/bookmark-deduper/) |
| 15 | 01 | backup-script | files | [backup-script](scripts/files/backup-script/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/backup-script/) |
| 15 | 02 | incremental-backup | files | [incremental-backup](scripts/files/incremental-backup/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/incremental-backup/) |
| 15 | 03 | zip-archiver | files | [zip-archiver](scripts/files/zip-archiver/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/zip-archiver/) |
| 15 | 04 | backup-rotator | files | [backup-rotator](scripts/files/backup-rotator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/backup-rotator/) |
| 15 | 05 | backup-verifier | files | [backup-verifier](scripts/files/backup-verifier/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/backup-verifier/) |
| 15 | 06 | folder-sync | files | [folder-sync](scripts/files/folder-sync/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/folder-sync/) |
| 15 | 07 | snapshot-differ | files | [snapshot-differ](scripts/files/snapshot-differ/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/snapshot-differ/) |
| 15 | 08 | tar-archiver | files | [tar-archiver](scripts/files/tar-archiver/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/tar-archiver/) |
| 15 | 09 | backup-size-estimator | files | [backup-size-estimator](scripts/files/backup-size-estimator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/backup-size-estimator/) |
| 15 | 10 | sync-conflict-finder | files | [sync-conflict-finder](scripts/files/sync-conflict-finder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/sync-conflict-finder/) |
| 16 | 01 | log-analyzer | system | [log-analyzer](scripts/system/log-analyzer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/log-analyzer/) |
| 16 | 02 | error-extractor | system | [error-extractor](scripts/system/error-extractor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/error-extractor/) |

<!-- INDEX:END -->

## How the web interface works
- `web/introspect.py` reads each script's argparse options, so a new script gets a form automatically. No extra code per tool.
- `web/build_site.py` builds the static site (one page per tool) and `.github/workflows/pages.yml` deploys it on every push.
- `web/dashboard.py` is the local server. It only listens on 127.0.0.1 and never runs anything through a shell.
- `web/check_links.py` checks that every live tool page and source file loads.
- `web/publish_site.py` publishes the site to the `gh-pages` branch from your own machine (`make publish`), for when GitHub Actions isn't available.
  While Pages is set to *Deploy from a branch* (`gh-pages`), run `make publish` after changing scripts to refresh the live site. To go back to automatic deploys, set Settings, Pages, Source to *GitHub Actions* again.
- `web/examples.json` and `web/samples.json` give every tool a working example (the **Try an example** button). Run `python web/run_examples.py` to test every tool at once; the test suite fails if a tool has no example.

## Contributing and security
See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) and [SECURITY.md](SECURITY.md). Release history lives in [CHANGELOG.md](CHANGELOG.md).

## License
MIT, see [LICENSE](LICENSE).
