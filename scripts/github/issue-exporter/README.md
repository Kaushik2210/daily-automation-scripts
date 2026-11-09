# issue-exporter

## Purpose
Take your issues out of GitHub and into a spreadsheet. The tool downloads the issues of a repository and turns them into CSV with one row per issue: number, title, state, author, assignees, labels, comment count, dates and link. Pull requests (which GitHub also lists as issues) are left out unless you ask for them. The CSV opens in Excel and Google Sheets, or feeds other scripts.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python issue_exporter.py owner/repo [--state open|closed|all] [--label bug --label docs] [--include-prs] [--out issues.csv]
python issue_exporter.py --from-file saved-issues.json
```
Several `--label` options mean the issue must have all of them. Without `--out` the CSV is printed; with it, a new file is written (an existing file is never overwritten). Public repositories work without a login; for private ones set `GITHUB_TOKEN` (`export GITHUB_TOKEN=ghp_...` or `$env:GITHUB_TOKEN = "ghp_..."` in PowerShell). The token is only sent to the GitHub API and never printed.

## Example
```bash
python issue_exporter.py --from-file gh-issues.json --state open
```
```
number,title,state,author,assignees,labels,comments,created,updated,closed,url
41,Login fails on Safari,open,mira,sam,bug;priority: high,4,2026-10-30,2026-10-30,,https://github.com/octo-demo/api-server/issues/41
40,"Add dark mode, please",open,tom,,enhancement,2,2026-10-25,2026-10-25,,https://github.com/octo-demo/api-server/issues/40
37,Support Python 3.14,open,sam,,enhancement;good first issue,1,2026-09-14,2026-09-14,,https://github.com/octo-demo/api-server/issues/37
```

## Notes
- Up to 1,000 issues are read by default (`--max-pages` changes that).
- Labels and assignees are joined with `;` inside their cell.
- `--from-file` takes a response saved with `curl https://api.github.com/repos/owner/repo/issues > issues.json`.
- The website demo reads the sample file; live exports work on your own computer.
