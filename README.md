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

**Progress: 252/300 done**

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
| 16 | 03 | log-tail-filter | system | [log-tail-filter](scripts/system/log-tail-filter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/log-tail-filter/) |
| 16 | 04 | nginx-log-parser | system | [nginx-log-parser](scripts/system/nginx-log-parser/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/nginx-log-parser/) |
| 16 | 05 | log-rotator | system | [log-rotator](scripts/system/log-rotator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/log-rotator/) |
| 16 | 06 | log-timeline | system | [log-timeline](scripts/system/log-timeline/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/log-timeline/) |
| 16 | 07 | top-ips-reporter | system | [top-ips-reporter](scripts/system/top-ips-reporter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/top-ips-reporter/) |
| 16 | 08 | status-code-counter | system | [status-code-counter](scripts/system/status-code-counter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/status-code-counter/) |
| 16 | 09 | pattern-counter | system | [pattern-counter](scripts/system/pattern-counter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/pattern-counter/) |
| 16 | 10 | log-merger | system | [log-merger](scripts/system/log-merger/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/log-merger/) |
| 17 | 01 | port-scanner | security | [port-scanner](scripts/security/port-scanner/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/port-scanner/) |
| 17 | 02 | ssl-expiry-checker | security | [ssl-expiry-checker](scripts/security/ssl-expiry-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/ssl-expiry-checker/) |
| 17 | 03 | dns-lookup | security | [dns-lookup](scripts/security/dns-lookup/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/dns-lookup/) |
| 17 | 04 | integrity-monitor | security | [integrity-monitor](scripts/security/integrity-monitor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/integrity-monitor/) |
| 17 | 05 | breach-password-checker | security | [breach-password-checker](scripts/security/breach-password-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/breach-password-checker/) |
| 17 | 06 | ssh-key-auditor | security | [ssh-key-auditor](scripts/security/ssh-key-auditor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/ssh-key-auditor/) |
| 17 | 07 | open-ports-lister | security | [open-ports-lister](scripts/security/open-ports-lister/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/open-ports-lister/) |
| 17 | 08 | whois-lookup | security | [whois-lookup](scripts/security/whois-lookup/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/whois-lookup/) |
| 17 | 09 | security-header-checker | security | [security-header-checker](scripts/security/security-header-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/security-header-checker/) |
| 17 | 10 | cert-chain-viewer | security | [cert-chain-viewer](scripts/security/cert-chain-viewer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/cert-chain-viewer/) |
| 18 | 01 | image-compressor | media | [image-compressor](scripts/media/image-compressor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/image-compressor/) |
| 18 | 02 | image-watermarker | media | [image-watermarker](scripts/media/image-watermarker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/image-watermarker/) |
| 18 | 03 | contact-sheet-maker | media | [contact-sheet-maker](scripts/media/contact-sheet-maker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/contact-sheet-maker/) |
| 18 | 04 | exif-stripper | media | [exif-stripper](scripts/media/exif-stripper/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/exif-stripper/) |
| 18 | 05 | audio-metadata-reader | media | [audio-metadata-reader](scripts/media/audio-metadata-reader/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/audio-metadata-reader/) |
| 18 | 06 | video-info-reporter | media | [video-info-reporter](scripts/media/video-info-reporter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/video-info-reporter/) |
| 18 | 07 | similar-image-finder | media | [similar-image-finder](scripts/media/similar-image-finder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/similar-image-finder/) |
| 18 | 08 | palette-extractor | media | [palette-extractor](scripts/media/palette-extractor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/palette-extractor/) |
| 18 | 09 | video-frame-grabber | media | [video-frame-grabber](scripts/media/video-frame-grabber/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/video-frame-grabber/) |
| 18 | 10 | sprite-sheet-builder | media | [sprite-sheet-builder](scripts/media/sprite-sheet-builder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/sprite-sheet-builder/) |
| 19 | 01 | markdown-link-checker | text | [markdown-link-checker](scripts/text/markdown-link-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/markdown-link-checker/) |
| 19 | 02 | markdown-to-html | text | [markdown-to-html](scripts/text/markdown-to-html/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/markdown-to-html/) |
| 19 | 03 | readme-linter | text | [readme-linter](scripts/text/readme-linter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/readme-linter/) |
| 19 | 04 | text-summarizer | text | [text-summarizer](scripts/text/text-summarizer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/text-summarizer/) |
| 19 | 05 | keyword-extractor | text | [keyword-extractor](scripts/text/keyword-extractor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/keyword-extractor/) |
| 19 | 06 | wordlist-spellcheck | text | [wordlist-spellcheck](scripts/text/wordlist-spellcheck/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/wordlist-spellcheck/) |
| 19 | 07 | docx-to-markdown | pdf-docs | [docx-to-markdown](scripts/pdf-docs/docx-to-markdown/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/pdf-docs/docx-to-markdown/) |
| 19 | 08 | readability-scorer | text | [readability-scorer](scripts/text/readability-scorer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/readability-scorer/) |
| 19 | 09 | srt-shifter | text | [srt-shifter](scripts/text/srt-shifter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/srt-shifter/) |
| 19 | 10 | glossary-builder | text | [glossary-builder](scripts/text/glossary-builder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/glossary-builder/) |
| 20 | 01 | dockerfile-linter | devops | [dockerfile-linter](scripts/devops/dockerfile-linter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/dockerfile-linter/) |
| 20 | 02 | env-template-generator | devops | [env-template-generator](scripts/devops/env-template-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/env-template-generator/) |
| 20 | 03 | requirements-checker | devops | [requirements-checker](scripts/devops/requirements-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/requirements-checker/) |
| 20 | 04 | ci-config-validator | devops | [ci-config-validator](scripts/devops/ci-config-validator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/ci-config-validator/) |
| 20 | 05 | makefile-target-lister | devops | [makefile-target-lister](scripts/devops/makefile-target-lister/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/makefile-target-lister/) |
| 20 | 06 | port-conflict-checker | devops | [port-conflict-checker](scripts/devops/port-conflict-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/port-conflict-checker/) |
| 20 | 07 | health-check-poller | devops | [health-check-poller](scripts/devops/health-check-poller/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/health-check-poller/) |
| 20 | 08 | cron-explainer | devops | [cron-explainer](scripts/devops/cron-explainer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/cron-explainer/) |
| 20 | 09 | docker-image-reporter | devops | [docker-image-reporter](scripts/devops/docker-image-reporter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/docker-image-reporter/) |
| 20 | 10 | release-tagger | devops | [release-tagger](scripts/devops/release-tagger/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/release-tagger/) |
| 21 | 01 | clipboard-history-logger | system | [clipboard-history-logger](scripts/system/clipboard-history-logger/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/clipboard-history-logger/) |
| 21 | 02 | snippet-manager | notion-productivity | [snippet-manager](scripts/notion-productivity/snippet-manager/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/snippet-manager/) |
| 21 | 03 | active-window-logger | system | [active-window-logger](scripts/system/active-window-logger/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/active-window-logger/) |
| 21 | 04 | screen-time-report | system | [screen-time-report](scripts/system/screen-time-report/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/screen-time-report/) |
| 21 | 05 | wallpaper-rotator | media | [wallpaper-rotator](scripts/media/wallpaper-rotator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/wallpaper-rotator/) |
| 21 | 06 | reminder-scheduler | notion-productivity | [reminder-scheduler](scripts/notion-productivity/reminder-scheduler/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/reminder-scheduler/) |
| 21 | 07 | folder-watcher | files | [folder-watcher](scripts/files/folder-watcher/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/folder-watcher/) |
| 21 | 08 | download-watcher | files | [download-watcher](scripts/files/download-watcher/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/files/download-watcher/) |
| 21 | 09 | screenshot-indexer | media | [screenshot-indexer](scripts/media/screenshot-indexer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/media/screenshot-indexer/) |
| 21 | 10 | text-expander | text | [text-expander](scripts/text/text-expander/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/text-expander/) |
| 22 | 01 | csv-schema-validator | data | [csv-schema-validator](scripts/data/csv-schema-validator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/csv-schema-validator/) |
| 22 | 02 | data-profiler | data | [data-profiler](scripts/data/data-profiler/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/data-profiler/) |
| 22 | 03 | sqlite-csv-importer | data | [sqlite-csv-importer](scripts/data/sqlite-csv-importer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/sqlite-csv-importer/) |
| 22 | 04 | sqlite-query-cli | data | [sqlite-query-cli](scripts/data/sqlite-query-cli/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/sqlite-query-cli/) |
| 22 | 05 | json-schema-validator | data | [json-schema-validator](scripts/data/json-schema-validator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/json-schema-validator/) |
| 22 | 06 | data-anonymizer | data | [data-anonymizer](scripts/data/data-anonymizer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/data-anonymizer/) |
| 22 | 07 | csv-differ | data | [csv-differ](scripts/data/csv-differ/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/csv-differ/) |
| 22 | 08 | parquet-converter | data | [parquet-converter](scripts/data/parquet-converter/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/parquet-converter/) |
| 22 | 09 | log-to-sqlite | data | [log-to-sqlite](scripts/data/log-to-sqlite/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/log-to-sqlite/) |
| 22 | 10 | pipeline-runner | data | [pipeline-runner](scripts/data/pipeline-runner/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/pipeline-runner/) |
| 23 | 01 | async-url-checker | web-scraping | [async-url-checker](scripts/web-scraping/async-url-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/async-url-checker/) |
| 23 | 02 | parallel-downloader | web-scraping | [parallel-downloader](scripts/web-scraping/parallel-downloader/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/parallel-downloader/) |
| 23 | 03 | api-recorder | web-scraping | [api-recorder](scripts/web-scraping/api-recorder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/api-recorder/) |
| 23 | 04 | api-smoke-tester | devops | [api-smoke-tester](scripts/devops/api-smoke-tester/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/api-smoke-tester/) |
| 23 | 05 | webhook-receiver | devops | [webhook-receiver](scripts/devops/webhook-receiver/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/webhook-receiver/) |
| 23 | 06 | rate-limited-fetcher | web-scraping | [rate-limited-fetcher](scripts/web-scraping/rate-limited-fetcher/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/rate-limited-fetcher/) |
| 23 | 07 | sitemap-crawler | web-scraping | [sitemap-crawler](scripts/web-scraping/sitemap-crawler/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/sitemap-crawler/) |
| 23 | 08 | link-graph-builder | web-scraping | [link-graph-builder](scripts/web-scraping/link-graph-builder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/web-scraping/link-graph-builder/) |
| 23 | 09 | mock-server | devops | [mock-server](scripts/devops/mock-server/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/mock-server/) |
| 23 | 10 | latency-benchmark | devops | [latency-benchmark](scripts/devops/latency-benchmark/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/devops/latency-benchmark/) |
| 24 | 01 | repo-health-scorer | github | [repo-health-scorer](scripts/github/repo-health-scorer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/repo-health-scorer/) |
| 24 | 02 | license-header-adder | github | [license-header-adder](scripts/github/license-header-adder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/license-header-adder/) |
| 24 | 03 | import-graph-builder | github | [import-graph-builder](scripts/github/import-graph-builder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/import-graph-builder/) |
| 24 | 04 | dead-code-finder | github | [dead-code-finder](scripts/github/dead-code-finder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/dead-code-finder/) |
| 24 | 05 | git-hook-installer | github | [git-hook-installer](scripts/github/git-hook-installer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/git-hook-installer/) |
| 24 | 06 | changed-files-finder | github | [changed-files-finder](scripts/github/changed-files-finder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/changed-files-finder/) |
| 24 | 07 | bulk-repo-cloner | github | [bulk-repo-cloner](scripts/github/bulk-repo-cloner/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/bulk-repo-cloner/) |
| 24 | 08 | git-large-file-finder | github | [git-large-file-finder](scripts/github/git-large-file-finder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/git-large-file-finder/) |
| 24 | 09 | history-secret-scanner | security | [history-secret-scanner](scripts/security/history-secret-scanner/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/security/history-secret-scanner/) |
| 24 | 10 | repo-activity-heatmap | github | [repo-activity-heatmap](scripts/github/repo-activity-heatmap/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/repo-activity-heatmap/) |
| 25 | 01 | weekly-github-report | github | [weekly-github-report](scripts/github/weekly-github-report/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/github/weekly-github-report/) |
| 25 | 02 | markdown-report-builder | text | [markdown-report-builder](scripts/text/markdown-report-builder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/text/markdown-report-builder/) |
| 25 | 03 | html-dashboard-builder | data | [html-dashboard-builder](scripts/data/html-dashboard-builder/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/html-dashboard-builder/) |
| 25 | 04 | chart-generator | data | [chart-generator](scripts/data/chart-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/chart-generator/) |
| 25 | 05 | sparkline-printer | data | [sparkline-printer](scripts/data/sparkline-printer/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/sparkline-printer/) |
| 25 | 06 | time-tracking-report | notion-productivity | [time-tracking-report](scripts/notion-productivity/time-tracking-report/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/time-tracking-report/) |
| 25 | 07 | invoice-generator | pdf-docs | [invoice-generator](scripts/pdf-docs/invoice-generator/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/pdf-docs/invoice-generator/) |
| 25 | 08 | expense-summary | data | [expense-summary](scripts/data/expense-summary/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/data/expense-summary/) |
| 25 | 09 | habit-streak-report | notion-productivity | [habit-streak-report](scripts/notion-productivity/habit-streak-report/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/notion-productivity/habit-streak-report/) |
| 25 | 10 | email-report-sender | email | [email-report-sender](scripts/email/email-report-sender/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/email/email-report-sender/) |
| 26 | 01 | process-monitor | system | [process-monitor](scripts/system/process-monitor/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/process-monitor/) |
| 26 | 02 | service-status-checker | system | [service-status-checker](scripts/system/service-status-checker/) | [Try it](https://kaushik2210.github.io/daily-automation-scripts/tools/system/service-status-checker/) |

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
