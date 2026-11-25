# bulk-repo-cloner

## Purpose
Clone many repositories in one go, from a text list, a GitHub user or organisation, or saved
GitHub API output. Forks and archived repositories are skipped unless you ask for them.

## Install
No dependencies beyond Python 3.11+ and `git`.

## Usage
```
python bulk_repo_cloner.py --list repos.txt --dest ~/code
python bulk_repo_cloner.py --user octocat --language Python --apply
python bulk_repo_cloner.py --org my-team --pattern "api-*" --depth 1 --jobs 8 --apply
python bulk_repo_cloner.py --from-json gh-repos.json --dest repos
```

- The list file takes one `owner/repo` or git URL per line, plus an optional folder name.
  Lines starting with `#` are ignored.
- `--update` runs `git pull --ff-only` in repositories that already exist.
- Set `GITHUB_TOKEN` (or `GH_TOKEN`) for private repositories and higher rate limits. The token is
  only sent to the GitHub API host and never goes into clone URLs or output.
- Nothing is cloned until you pass `--apply`. Existing folders are never overwritten.
- Exit code is 1 if any clone fails or nothing matches.

## Example
`--from-json gh-repos.json --dest repos`

```
4 repositories -> repos/
  api-server               will clone        https://github.com/octo-demo/api-server.git [Python]
  web-app                  will clone        https://github.com/octo-demo/web-app.git [TypeScript]
  data-tools               will clone        https://github.com/octo-demo/data-tools.git [Python]
  dotfiles                 will clone        https://github.com/octo-demo/dotfiles.git [Shell]

Dry run: 4 action(s). Use --apply to start (4 at once).
```

## Notes
- The browser demo shows the plan only, since it can't run git.
- `--ssh` switches API repositories to their SSH URLs.
