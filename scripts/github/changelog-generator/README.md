# changelog-generator

## Purpose
Write release notes from your commit history. Commits that follow the conventional format (`feat: ...`, `fix(scope): ...`, `feat!: ...`) are grouped into Features, Bug fixes, Documentation and so on, with breaking changes called out first.

## Install
Standard library only, Python 3.11+, and `git` on your PATH for real repositories.

## Usage
```bash
python changelog_generator.py [--repo PATH] [--since TAG_OR_DATE] [--version 1.2.0]
                              [--date YYYY-MM-DD] [-o CHANGELOG.md --apply]
python changelog_generator.py --log git-log.txt
```
By default it reads `git log` from the repository; `--since v1.1.0` limits it to commits after that tag. The section is printed; with `-o` and `--apply` it is added under the `# Changelog` title, above older releases. To use a saved history instead (for example on the website), create one with:
```bash
git log --date=short --pretty=format:'@@%H%x1f%an%x1f%ae%x1f%ad%x1f%s' > git-log.txt
```

## Example
```bash
python changelog_generator.py --log git-log.txt --version 1.2.0 --date 2026-01-14
```
```
## [1.2.0] - 2026-01-14

### BREAKING CHANGES

- drop support for Node 16 (d0e1f2a)

### Features

- add password reset flow (a1b2c3d)
- **ui:** add dark mode toggle (f6a7b8c)
- export orders as CSV (c9d0e1f)
- add a very long subject line that goes well beyond the recommended seventy two character limit (e1f2a3b)
- initial project setup (f2a3b4c)

### Bug fixes

- handle empty cart in checkout (b2c3d4e)
- drop support for Node 16 (d0e1f2a)

### Refactoring

- split the router into modules (e5f6a7b)

### Documentation

- update install guide (c3d4e5f)

### Chores

- bump dependencies (b8c9d0e)
```

## Notes
- Commits without a recognised `type:` prefix are counted and left out rather than guessed at.
- Each entry ends with the short commit hash so you can trace it.
- Review the result: a changelog is for people, so reword anything unclear.
