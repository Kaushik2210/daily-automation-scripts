# release-notifier

## Purpose
Hear about new versions of the tools you depend on without watching every repository. Give the tool a list of repositories and it looks up each one's latest release, compares it with the tag it remembered last time, and prints what's new with the release title, date, the first lines of the notes and a link. The exit code is 1 when there is something new, so cron, Task Scheduler or a shell `if` can send you an alert.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python release_notifier.py owner/repo [owner/repo ...] --state releases.json
python release_notifier.py --file watched.txt --state releases.json [--include-prereleases]
python release_notifier.py --releases saved-releases.json --state releases.json
```
The first time a repository is seen its current tag is only remembered (a "baseline"); add `--report-all` to report it as new. After that, a changed tag is reported as new and saved, unless you add `--no-update`. Pre-releases and drafts are ignored by default. Without a token GitHub allows 60 requests an hour, enough for dozens of repositories checked a few times a day; `export GITHUB_TOKEN=ghp_...` raises the limit and is never printed.

## Example
```bash
python release_notifier.py --releases gh-releases.json --state release-state.json --no-update
```
```
*  octo-demo/api-server: NEW v2.4.0
     Pagination and speedups, published 2026-11-03
       Adds pagination.
       faster queries
       fixes #41
     https://github.com/octo-demo/x/releases/tag/v2.4.0
   octo-demo/web-app: v1.9.0 (nothing new)
   octo-demo/data-tools: v0.5.0-rc1 is a pre-release, ignored
   octo-demo/dotfiles: no releases yet

1 new release(s) across 4 repositories.
```

## Notes
- State is a small JSON file mapping each repository to the last tag seen.
- A repository with no releases is reported as such; it isn't an error.
- If a lookup fails (network or rate limit) that repository is skipped for this run and the exit code is 1.
- The website demo reads saved releases; live checks work on your own computer.
