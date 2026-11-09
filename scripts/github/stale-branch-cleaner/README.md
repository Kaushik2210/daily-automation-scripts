# stale-branch-cleaner

## Purpose
Tidy up branches that are finished. The tool lists branches that are already merged into your main branch and haven't had a commit for a while (90 days by default), oldest first. Nothing is deleted unless you add `--apply`, and even then only those branches are removed. Unmerged work, the base branch, protected names (`main`, `master`, `develop`, `dev`, `trunk`) and the branch you're on are always left alone.

## Install
Standard library only, Python 3.11+, and `git` on your PATH for real repositories.

## Usage
```bash
python stale_branch_cleaner.py [--repo PATH] [--base main] [--days 90] [--apply]
python stale_branch_cleaner.py --remote [--apply]
python stale_branch_cleaner.py --refs branches.txt --merged merged.txt
```
Local branches are deleted with `git branch -d`, which refuses to remove anything unmerged. With `--remote` it works on `origin`'s branches and `--apply` runs `git push origin --delete` for each one, so run the dry run first and read the list. `--refs` and `--merged` read saved output instead of git (dry run only); create them with:
```bash
git for-each-ref --format='%(refname:short)%1f%(committerdate:short)%1f%(authorname)%1f%(subject)' refs/heads > branches.txt
git branch --merged main > merged.txt
```

## Example
```bash
python stale_branch_cleaner.py --refs branches.txt --merged merged.txt --today 2026-01-13
```
```
1 stale merged local branch(es) (merged into main, idle 90+ days) out of 5:
  old/experiment                225 days  Max Weber

Dry run - nothing deleted. Add --apply to delete the branches listed above.
```

## Notes
- "Merged" is judged by git from the branch history, so squash-merged branches may not be recognised.
- A deleted local branch can be restored from `git reflog` for a while; a deleted remote branch is harder to bring back.
- Add a `--base` other than `main` if your default branch has a different name.
