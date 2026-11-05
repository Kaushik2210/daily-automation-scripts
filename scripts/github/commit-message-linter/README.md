# commit-message-linter

## Purpose
Keep commit history readable. It checks subjects against the conventional-commits format (`feat: add login`, `fix(cart): handle empty cart`), a length limit, trailing periods and vague messages such as `wip`. Use it on recent commits, on a saved log, or on a single message from a git hook.

## Install
Standard library only, Python 3.11+, and `git` on your PATH for real repositories.

## Usage
```bash
python commit_message_linter.py [--repo PATH] [-n COUNT] [--style conventional|free] [--max-length N]
python commit_message_linter.py --message "feat: add login"
python commit_message_linter.py --log git-log.txt
```
By default it lints the last 20 commits in the repository. To use a saved history instead (for example on the website), create one with:
```bash
git log --date=short --pretty=format:'@@%H%x1f%an%x1f%ae%x1f%ad%x1f%s' > git-log.txt
```
The exit code is 1 when any message has a problem, so it can run in CI or a `commit-msg` hook.

## Example
```bash
python commit_message_linter.py --log git-log.txt
```
```
d4e5f6a  wip stuff
        - not in the form 'type: description' (types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert)
a7b8c9d  Fixed bug.
        - subject ends with a period
        - not in the form 'type: description' (types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert)
e1f2a3b  feat: add a very long subject line that goes well beyond the...
        - subject is 100 characters (limit 72)
12 message(s) checked, 3 with problems.
```

## Notes
- Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert.
- `--style free` skips the type rule and only checks length, spacing and vagueness.
- Read-only.
