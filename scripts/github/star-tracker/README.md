# star-tracker

## Purpose
Watch your projects grow. Each time you run it, the tool reads the star count (and forks) of every one of your public repositories, compares them with the readings saved last time and shows how many stars each gained or lost, then appends today's numbers to a CSV history file. Run it daily or weekly from cron or Task Scheduler and you get a record you can chart in any spreadsheet.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python star_tracker.py USER --log stars.csv [--no-record] [--include-forks]
python star_tracker.py --from-file saved-repos.json --log stars.csv
```
The log has the columns `date, repo, stars, forks`. A repository is recorded at most once per day, so re-running the same day is safe. Forks are skipped unless you pass `--include-forks`. Without a token GitHub allows 60 requests an hour, which is plenty; to raise that, set `GITHUB_TOKEN` (`export GITHUB_TOKEN=ghp_...`). It is only sent to the GitHub API and never printed.

## Example
```bash
python star_tracker.py --from-file gh-repos.json --log stars.csv --no-record --today 2026-11-09
```
```
octo-demo/api-server    1,240  +140 since 2026-10-01
octo-demo/web-app         860  +40 since 2026-10-01
octo-demo/data-tools      310  +0 since 2026-10-01
octo-demo/old-lib         120  first reading
octo-demo/dotfiles         45  -5 since 2026-10-01
Total                   2,575  +175 across repos with history
```

## Notes
- `--no-record` shows the comparison without adding a row, handy for a quick look.
- A repository seen for the first time says "first reading"; its change appears on the next run.
- Stars can also fall when people un-star, so negative numbers are normal.
- The website demo reads the sample files; live lookups work on your own computer.
