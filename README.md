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

**Progress: 12/300 done**

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

<!-- INDEX:END -->

## How the web interface works
- `web/introspect.py` reads each script's argparse options, so a new script gets a form automatically. No extra code per tool.
- `web/build_site.py` builds the static site (one page per tool) and `.github/workflows/pages.yml` deploys it on every push.
- `web/dashboard.py` is the local server. It only listens on 127.0.0.1 and never runs anything through a shell.
- `web/check_links.py` checks that every live tool page and source file loads.

## Contributing and security
See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) and [SECURITY.md](SECURITY.md). Release history lives in [CHANGELOG.md](CHANGELOG.md).

## License
MIT, see [LICENSE](LICENSE).
