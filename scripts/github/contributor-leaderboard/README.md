# contributor-leaderboard

## Purpose
See who really builds a project. The tool fetches a repository's contributors and ranks them by commits, showing each person's count, share of all commits and a small bar, plus how much of the work the top few did. Bots such as Dependabot can be filtered out so the ranking reflects people.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python contributor_leaderboard.py owner/repo [--top 10] [--exclude-bots]
python contributor_leaderboard.py --from-file saved-contributors.json
```
Public repositories work without a login (60 requests an hour). For private ones, or a higher limit, set `GITHUB_TOKEN` (`export GITHUB_TOKEN=ghp_...`, or `$env:GITHUB_TOKEN = "ghp_..."` in PowerShell). It is only sent to the GitHub API and never printed. `--from-file` reads a response saved with `curl https://api.github.com/repos/owner/repo/contributors > contributors.json`.

## Example
```bash
python contributor_leaderboard.py --from-file gh-contributors.json --top 5 --exclude-bots
```
```
  1. sam      412   50.2%  ########################
  2. mira     268   32.6%  ################
  3. tom       97   11.8%  ######
  4. lee       41    5.0%  ##
  5. ana        3    0.4%  #

5 contributor(s), 821 commits. The top 5 wrote 100%.
```

## Notes
- Counts are commits to the default branch as GitHub reports them; one person using several email addresses can appear more than once.
- Anonymous contributors (commits not linked to an account) are listed by their commit name.
- For very large repositories GitHub refuses to compute this list and answers 403.
- The website demo reads the sample file; live lookups work on your own computer.
