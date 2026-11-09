# github-stats-reporter

## Purpose
Get the numbers behind a GitHub profile or project at a glance. Give it a repository (`owner/repo`) to see its stars, forks, open issues, language, licence and when it was last pushed, or give it a user name for a roll-up of all their public repositories: total stars and forks, the most-used languages, how many were active this month, and the top repositories by stars.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python github_stats_reporter.py octocat/Hello-World
python github_stats_reporter.py octocat [--include-forks]
python github_stats_reporter.py --from-file saved-response.json
```
Public data needs no login, but anonymous requests are limited to 60 an hour. For 5,000 an hour set a token in the environment: `export GITHUB_TOKEN=ghp_...` (PowerShell: `$env:GITHUB_TOKEN = "ghp_..."`). The token is only sent to the GitHub API and is never printed. `--from-file` reads a response you saved earlier (`curl https://api.github.com/users/octocat/repos > repos.json`).

## Example
```bash
python github_stats_reporter.py --from-file gh-repos.json --today 2026-11-09
```
```
5 repositories (+1 forks left out)
  Stars: 2,575    Forks: 299    Pushed in the last 30 days: 2
  Languages: Python (2), TypeScript (1), Shell (1), Go (1)

Top 5 by stars:
   1,240 *  api-server           Python       pushed 4 day(s) ago
     860 *  web-app              TypeScript   pushed 1 day(s) ago
     310 *  data-tools           Python       pushed 58 day(s) ago
     120 *  old-lib              Go           pushed 21 month(s) ago
      45 *  dotfiles             Shell        pushed 39 day(s) ago
```

## Notes
- Forks are left out of the totals unless you pass `--include-forks`.
- Only the first 500 repositories of a user are read.
- Set `GITHUB_API_URL` to use a GitHub Enterprise server.
- The website demo reads the sample file; live lookups work on your own computer.
