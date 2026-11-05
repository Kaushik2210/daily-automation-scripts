# repo-size-reporter

## Purpose
Find out why a repository is heavy. It reports the size of the working tree and of the `.git` history separately, lists the biggest files, and breaks the total down by file type, so an accidentally committed video or data dump stands out.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python repo_size_reporter.py [FOLDER] [-n TOP] [--include-deps]
```
`node_modules` and virtual environments are skipped unless you pass `--include-deps`. If the folder contains a `.git` directory its size is shown on its own line.

## Example
```bash
python repo_size_reporter.py demo-project
```
```
Working tree: 723 B in 5 file(s)

Largest 5 file(s):
      254 B  src/app.js
      206 B  package.json
      128 B  src/utils.js
       93 B  tests/app.test.js
       42 B  LICENSE

By file type:
  .js         3 file(s)      475 B   66%
  .json       1 file(s)      206 B   28%
  (none)      1 file(s)       42 B    6%
```

## Notes
- Read-only.
- A very large `.git` size usually means big files were committed at some point, even if they were deleted later; they remain in the history.
- Sizes are the files' byte sizes, not disk blocks, so they can differ slightly from your file manager.
