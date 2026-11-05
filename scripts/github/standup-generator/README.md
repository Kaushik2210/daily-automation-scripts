# standup-generator

## Purpose
Answer "what did you do yesterday?" in seconds. It reads your recent git commits and writes a standup with yesterday's work, today's work so far and a blockers line. Mondays and weekends look back to Friday, and commit subjects such as `feat(ui): add dark mode` are tidied into `Add dark mode`.

## Install
Standard library only, Python 3.11+, and `git` on your PATH for real repositories.

## Usage
```bash
python standup_generator.py [--repo PATH] [--author TEXT] [--today YYYY-MM-DD] [--raw]
python standup_generator.py --log git-log.txt --author ada
```
By default it runs `git log` in the repository. To work from a saved history (for example on a machine without git, or on the website), save one with:
```bash
git log --date=short --pretty=format:'@@%H%x1f%an%x1f%ae%x1f%ad%x1f%s' > git-log.txt
```
`--author` matches part of the author's name or email.

## Example
```bash
python standup_generator.py --log git-log.txt --author Ada --today 2026-01-13
```
```
Standup for Tue 2026-01-13 (Ada)

Yesterday (Mon 2026-01-12):
- Update install guide (c3d4e5f)
- Split the router into modules (e5f6a7b)

Today so far:
- Add password reset flow (a1b2c3d)

Blockers:
- None
```

## Notes
- Read-only. It never changes your repository.
- Without `--author` the standup includes everyone's commits, which suits a team summary.
- `--raw` keeps the original commit subjects instead of tidying them.
