# git-hook-installer

## Purpose
Catch mistakes before they reach the repository. Git can run a script at certain moments (a "hook"); this tool installs ready-made ones in one command: **pre-commit** and **pre-push** run the checks you choose (for example `ruff check .` and your tests) and stop the commit or push if one fails, **commit-msg** requires Conventional Commit messages (`feat: add search`, `fix(api): handle nulls`), and **protect-branch** refuses commits made directly on `main` or `master`. Each hook is a small, readable shell script.

## Install
Standard library only, Python 3.11+. Hooks run with the `sh` that comes with Git (including Git for Windows).

## Usage
```bash
python git_hook_installer.py list
python git_hook_installer.py install pre-commit commit-msg [--preset python|node|go] [--command "make lint"] [--apply]
python git_hook_installer.py uninstall commit-msg [--apply]
```
Run it inside the repository, or point to it with `--repo`. **Dry run by default:** it shows each hook's location and the first lines of its script. With `--apply` the hooks are written and made executable. A hook that someone else wrote is never overwritten: it is renamed to `NAME.bak` first. Hooks installed by this tool are marked with a comment, so reinstalling replaces them and `uninstall` removes only those. `--command` can be repeated; presets add the usual commands for Python, Node or Go. `--hooks-dir` installs into another folder.

## Example
```bash
python git_hook_installer.py install commit-msg pre-commit --hooks-dir hooks-demo/ --preset python
```
```
would install  commit-msg -> hooks-demo\commit-msg  (existing hook is kept as commit-msg.bak)
    first_line=$(head -n 1 "$1")
    case "$first_line" in Merge*|Revert*|fixup!*|squash!*) exit 0 ;; esac
    if echo "$first_line" | grep -Eq '^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?: .+'; then exit 0; fi
    echo "commit-msg: use the form type: description, e.g. feat: add search" >&2
would install  pre-commit -> hooks-demo\pre-commit  (new)
    set -e
    echo "pre-commit: ruff check ."
    ruff check . || { echo "pre-commit: failed: ruff check ." >&2; exit 1; }
    echo "pre-commit: python -m pytest -q"

Dry run. Use --apply to do it.
```

## Notes
- Hooks live in `.git/hooks`, which isn't shared by `git clone`; each developer installs them (or a team keeps this command in its setup docs).
- In an emergency, `git commit --no-verify` skips the commit hooks; CI is the real safety net.
- Use `commit-message-linter` to check messages that are already written.
- The website demo shows what would be installed; installing hooks works on your own computer.
