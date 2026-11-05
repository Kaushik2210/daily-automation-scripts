# git-log-summarizer

## Purpose
Get the shape of a project's history at a glance: who committed how much, how activity moves from week to week, and what kinds of changes dominate (features, fixes, docs). Types are read from conventional commit prefixes such as `feat:` and `fix:`.

## Install
Standard library only, Python 3.11+, and `git` on your PATH for real repositories.

## Usage
```bash
python git_log_summarizer.py [--repo PATH] [--since YYYY-MM-DD]
python git_log_summarizer.py --log git-log.txt
```
By default it runs `git log` in the repository. To use a saved history instead (for example on the website), create one with:
```bash
git log --date=short --pretty=format:'@@%H%x1f%an%x1f%ae%x1f%ad%x1f%s' > git-log.txt
```

## Example
```bash
python git_log_summarizer.py --log git-log.txt
```
```
12 commit(s) by 3 author(s)

By author
     5  Ada Lovelace
     4  Lin Chen
     3  Max Weber

By week            Ada       Lin       Max   total
  2026-W02         2         3         2       7
  2026-W03         3         1         1       5

By type
     5  feat
     2  fix
```

## Notes
- Weeks are ISO weeks (they start on Monday), shown as `YYYY-Www`.
- Commits without a `type:` prefix are counted as `other`.
- Read-only.
