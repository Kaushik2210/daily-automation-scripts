# branch-lister

## Purpose
See which branches are alive and which have been forgotten. Every local branch is listed newest first with its last commit date, a friendly age (`4d ago`, `3mo ago`), the author and the last commit message, and branches that haven't moved in a while are marked `STALE`.

## Install
Standard library only, Python 3.11+, and `git` on your PATH for real repositories.

## Usage
```bash
python branch_lister.py [--repo PATH] [--stale-days N]
python branch_lister.py --refs branches.txt [--today YYYY-MM-DD]
```
By default it asks git for the local branches. To use a saved list instead (for example on the website), create one with:
```bash
git for-each-ref --format='%(refname:short)%1f%(committerdate:short)%1f%(authorname)%1f%(subject)' refs/heads > branches.txt
```
`--stale-days` sets how many days of silence count as stale (default 90).

## Example
```bash
python branch_lister.py --refs branches.txt --today 2026-01-13
```
```
main               2026-01-13     today  Ada Lovelace  feat: add password reset flow
feature/dark-mode  2026-01-09    4d ago  Lin Chen      feat(ui): add dark mode toggle
release/1.0        2025-12-15    4w ago  Ada Lovelace  chore: prepare release 1.0
fix/cart-bug       2025-11-20    7w ago  Lin Chen      fix: cart total rounding
old/experiment     2025-06-02   7mo ago  Max Weber     try a new layout  STALE
5 branch(es), 1 older than 90 days.
```

## Notes
- Read-only: it never deletes or changes a branch. When you are ready to clean up, check `git branch --merged` first.
- `--today` pins the date, which makes the output repeatable.
- Ages are measured from each branch's last commit date.
