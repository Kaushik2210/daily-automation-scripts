# repo-health-scorer

## Purpose
Find out how healthy a project looks to a newcomer, and what to fix first. The tool inspects a project folder and awards points for the things that make a repository trustworthy: a README (with enough detail and Install/Usage sections), a LICENSE, automated tests, CI configuration, a `.gitignore`, a dependency list, CONTRIBUTING and CHANGELOG files, a SECURITY or CODE_OF_CONDUCT file, and no committed junk such as `node_modules`, `__pycache__` or `.env` (unless your `.gitignore` already hides it). It prints a percentage, a letter grade and a checklist with advice for every missing piece.

## Install
Standard library only, Python 3.11+. Nothing to install. `--git` also needs the `git` command.

## Usage
```bash
python repo_health_scorer.py [FOLDER] [--min-score 60] [--git]
```
Without a folder it scores the current one. Test files are recognised for Python, JavaScript/TypeScript and Go; CI for GitHub Actions, GitLab, Travis, Jenkins, Azure and others. `--git` adds a "Recent activity" check (last commit within 90 days is full marks) when the folder is a git repository's own root. The exit code is 1 when the score is below `--min-score`, so it can guard a pull request or a template repo.

## Example
```bash
python repo_health_scorer.py pyproj/
```
```
pyproj: 12 file(s), health 78% (grade B)

  [PASS] README                 10/10
  [MISS] README detail           0/5   Expand the README (at least ~100 words)
  [PASS] README install/usage    5/5 
  [PASS] License                10/10
  [PASS] Tests                  15/15
  [PASS] CI                     15/15
  [PASS] .gitignore              5/5 
  [PASS] Dependencies listed     5/5 
  [MISS] CONTRIBUTING            0/5   Add CONTRIBUTING.md for newcomers
  [MISS] CHANGELOG               0/5   Keep a CHANGELOG.md of notable changes
  [MISS] SECURITY / conduct      0/5   Add SECURITY.md or CODE_OF_CONDUCT.md
  [PASS] No junk committed       5/5 

70 of 90 points.
```

## Notes
- The score is a conversation starter, not a verdict: a tiny script doesn't need a CHANGELOG.
- Folders like `.git`, `node_modules`, `.venv` and `build` are not scanned.
- Use `repo-readme-generator` to draft a README and `gitignore-generator` for a `.gitignore`.
