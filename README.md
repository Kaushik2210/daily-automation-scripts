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

## Categories
`files`, `pdf-docs`, `github`, `email`, `web-scraping`, `notion-productivity`, `data`, `system`, `security`, `media`, `text`, `devops`

## Index
The table below is rebuilt by `python tools/update_index.py` from `PLAN.md` and the script folders. Don't edit between the markers by hand.

<!-- INDEX:START -->

**Progress: 76/300 done**

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

<!-- INDEX:END -->

## How the web interface works
- `web/introspect.py` reads each script's argparse options, so a new script gets a form automatically. No extra code per tool.
- `web/build_site.py` builds the static site (one page per tool) and `.github/workflows/pages.yml` deploys it on every push.
- `web/dashboard.py` is the local server. It only listens on 127.0.0.1 and never runs anything through a shell.
- `web/check_links.py` checks that every live tool page and source file loads.
- `web/examples.json` and `web/samples.json` give every tool a working example (the **Try an example** button). Run `python web/run_examples.py` to test every tool at once; the test suite fails if a tool has no example.

## Contributing and security
See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) and [SECURITY.md](SECURITY.md). Release history lives in [CHANGELOG.md](CHANGELOG.md).

## License
MIT, see [LICENSE](LICENSE).
