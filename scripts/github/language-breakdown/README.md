# language-breakdown

## Purpose
Find out what you actually write. The tool looks at all of a user's public repositories and shows the share of each language as a text bar chart. By default it counts repositories by their main language; you can weight the share by stars or repository size instead, or ask GitHub for real code bytes per language for the most accurate picture.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python language_breakdown.py USER [--weight count|stars|size] [--skip-archived] [--include-forks]
python language_breakdown.py USER --bytes [--max-repos 30]
python language_breakdown.py --from-file saved-repos.json
```
`--weight size` uses the repository size GitHub reports, which is a quick stand-in for "how much code". `--bytes` makes one extra request per repository for exact language bytes (limited by `--max-repos`; forks are skipped). Without a token GitHub allows 60 requests an hour; set `GITHUB_TOKEN` (`export GITHUB_TOKEN=ghp_...`) for more. It is only sent to the GitHub API and never printed.

## Example
```bash
python language_breakdown.py --from-file gh-repos.json --weight size
```
```
Languages by size:

TypeScript      60.5%  ##################             12,800 KB
Python          28.8%  #########                      6,100 KB
Go               9.9%  ###                            2,100 KB
Shell            0.7%  #                              150 KB
```

## Notes
- Repositories with no detected language are ignored.
- Forks are left out unless you pass `--include-forks`.
- A repository's "main language" is GitHub's best guess; it can differ from the code bytes view.
- The website demo reads the sample file; live lookups work on your own computer.
