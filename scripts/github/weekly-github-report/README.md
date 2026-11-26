# weekly-github-report

## Purpose
Write a weekly activity report across several GitHub repositories: commits, pull requests opened
and merged, issues opened and closed, top contributors and what is still waiting for review.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python weekly_github_report.py --repos me/api me/web
python weekly_github_report.py --repos me/api me/web --week-ending 2026-11-22 --output week-47.md
python weekly_github_report.py --repos me/api --days 14 --format json
python weekly_github_report.py --from-json activity.json
```

Set `GITHUB_TOKEN` (or `GH_TOKEN`) for private repositories and higher rate limits. The token is
only sent to the GitHub API host. `--output` refuses to overwrite an existing file.

The saved format for `--from-json` is `{"since", "until", "repos": {"owner/name": {"commits": [...],
"pulls": [...], "issues": [...]}}}`; the example below uses one.

## Example
`--from-json gh-weekly.json`

```
# Weekly GitHub report: 2026-11-16 to 2026-11-22

| Repository | Commits | PRs opened | PRs merged | Issues opened | Issues closed |
|---|---|---|---|---|---|
| octo-demo/api-server | 14 | 2 | 2 | 2 | 2 |
| octo-demo/web-app | 9 | 2 | 1 | 1 | 1 |
| **Total** | 23 | 4 | 3 | 3 | 3 |

## Top contributors

- mira: 7 commit(s)
- tom: 7 commit(s)
- sam: 6 commit(s)
- lee: 3 commit(s)

## Merged this week

- octo-demo/api-server#212 Add pagination to the users endpoint (@mira)
- octo-demo/api-server#207 Bump dependencies (@tom)
- octo-demo/web-app#212 Add pagination to the users endpoint (@mira)

## Issues closed

- octo-demo/api-server#41 Login fails on Safari
- octo-demo/api-server#39 Slow search on large repos
- octo-demo/web-app#39 Slow search on large repos

## Still open

- octo-demo/api-server#214 Retry failed webhooks (@sam, opened 2026-11-18)
- octo-demo/web-app#214 Retry failed webhooks (@sam, opened 2026-11-18)
```

## Notes
- The week runs to the end of `--week-ending` (UTC), `--days` days back. The default is today.
- Only the newest 1000 items per list are read for each repository.
- Pull requests are not counted as issues, even though GitHub lists them there.
