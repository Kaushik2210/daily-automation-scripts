# rate-limit-checker

## Purpose
Know how close you are to GitHub's API limits before a script of yours starts failing. The tool asks GitHub's rate-limit endpoint (which doesn't use up any quota itself) and shows each limit - core, search, GraphQL and others - with how many requests are left, how many you've used and when the counter resets. The exit code is 1 when any limit is nearly used up, so it works as a guard at the start of a cron job.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python rate_limit_checker.py [--warn-below 10]
python rate_limit_checker.py --from-file saved-rate-limit.json
```
With no token set, GitHub counts you as anonymous: 60 requests an hour. With a token (`export GITHUB_TOKEN=ghp_...`, or `$env:GITHUB_TOKEN = "ghp_..."` in PowerShell) the core limit is 5,000 an hour. The tool says which one it used; the token is only sent to the GitHub API and never printed. `--warn-below` is the percentage left that triggers the warning and exit code 1 (default 10).

## Example
```bash
python rate_limit_checker.py --from-file gh-rate-limit.json --now 2026-11-09T11:18:30
```
```
core          179 of 5,000  left (  3.6%)  used 4,821  resets 12:00 UTC in 41m 30s  <-- LOW
graphql     5,000 of 5,000  left (100.0%)  used 0  resets 12:50 UTC in 1h 31m
search         26 of 30     left ( 86.7%)  used 4  resets 11:10 UTC already reset
```

## Notes
- Times are shown in UTC.
- Limits that GitHub reports as zero (not available to you) are left out.
- `--now` only exists so examples and tests give the same answer every time.
- The website demo reads a saved response; a live check works on your own computer.
