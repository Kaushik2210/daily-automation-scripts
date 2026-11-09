# pr-review-queue

## Purpose
Never lose track of a review you owe. The tool asks GitHub for every open pull request where your review has been requested, then lists them with the longest-waiting first, showing how many days each has been open, who wrote it, how many comments it has and a direct link. Drafts are hidden by default, and slow ones are flagged.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
export GITHUB_TOKEN=ghp_...    # PowerShell: $env:GITHUB_TOKEN = "ghp_..."
python pr_review_queue.py [--org my-org] [--include-drafts] [--warn-days 7]
python pr_review_queue.py --user octocat
python pr_review_queue.py --from-file saved-search.json
```
`@me` (the default) needs a token so GitHub knows who you are; a token with read access to the repositories is enough. With `--user NAME` the search works without a token for public repositories. The token is only sent to the GitHub API and is never printed. `--from-file` reads a saved response, for example from `curl -H "Authorization: Bearer $GITHUB_TOKEN" "https://api.github.com/search/issues?q=is:pr+is:open+review-requested:@me"`.

## Example
```bash
python pr_review_queue.py --from-file gh-review-prs.json --today 2026-11-09
```
```
3 pull request(s) waiting for review:

 19d  octo-demo/web-app#88  Upgrade React to 19  <-- waiting a while
      by tom, 9 comment(s)  https://github.com/octo-demo/web-app/pull/88
  8d  octo-demo/api-server#212  Add pagination to the users endpoint  <-- waiting a while
      by mira, 3 comment(s)  https://github.com/octo-demo/api-server/pull/212
  1d  octo-demo/data-tools#14  Fix flaky chart test
      by lee, 0 comment(s)  https://github.com/octo-demo/data-tools/pull/14
```

## Notes
- Only review requests addressed to you personally are included, not ones sent to a team you belong to.
- At most 100 pull requests are listed.
- The website demo reads the sample file; live lookups work on your own computer.
