# git-author-stats

## Purpose
See who did what in a repository: commits, share of the total, lines added and deleted, how many different days each person committed, and when they were active. Handy for retrospectives and for crediting contributors.

## Install
Standard library only, Python 3.11+, and `git` on your PATH for real repositories.

## Usage
```bash
python git_author_stats.py [--repo PATH] [--by name|email] [--sort commits|lines]
python git_author_stats.py --log git-log.txt
```
By default it runs `git log --numstat` in the repository. To use a saved history instead (for example on the website), create one with:
```bash
git log --numstat --date=short --pretty=format:'@@%H%x1f%an%x1f%ae%x1f%ad%x1f%s' > git-log.txt
```

## Example
```bash
python git_author_stats.py --log git-log.txt
```
```
author             commits  share   added  deleted  days  active
Ada Lovelace             5    42%     883       87     4  2026-01-05 to 2026-01-13
Lin Chen                 4    33%     261        6     4  2026-01-05 to 2026-01-12
Max Weber                3    25%      13        8     3  2026-01-06 to 2026-01-12
12 commit(s), 3 author(s).
```

## Notes
- Use `--by email` when the same person commits under several names.
- Line counts are not a measure of quality, and binary files are not counted.
- Read-only.
