# daily-automation-scripts

[![CI](https://github.com/Kaushik2210/daily-automation-scripts/actions/workflows/ci.yml/badge.svg)](https://github.com/Kaushik2210/daily-automation-scripts/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Platforms](https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/lint-ruff-261230)](https://docs.astral.sh/ruff/)

A 30-day challenge: ten small, useful automation scripts every day, 300 in total. Each script lives in its own folder, comes with a README and tests, and lands as its own commit and push.

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

**Progress: 6/300 done**

| Day | # | Script | Category | Link |
| --- | --- | --- | --- | --- |
| 01 | 01 | bulk-file-renamer | files | [bulk-file-renamer](scripts/files/bulk-file-renamer/) |
| 01 | 02 | duplicate-file-finder | files | [duplicate-file-finder](scripts/files/duplicate-file-finder/) |
| 01 | 03 | folder-organizer | files | [folder-organizer](scripts/files/folder-organizer/) |
| 01 | 04 | empty-folder-cleaner | files | [empty-folder-cleaner](scripts/files/empty-folder-cleaner/) |
| 01 | 05 | file-size-lister | files | [file-size-lister](scripts/files/file-size-lister/) |
| 01 | 06 | old-file-finder | files | [old-file-finder](scripts/files/old-file-finder/) |

<!-- INDEX:END -->

## Contributing and security
See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) and [SECURITY.md](SECURITY.md). Release history lives in [CHANGELOG.md](CHANGELOG.md).

## License
MIT, see [LICENSE](LICENSE).
