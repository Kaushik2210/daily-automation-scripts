# todo-comment-finder

## Purpose
Turn scattered reminders in your code into a list. It finds `TODO`, `FIXME`, `HACK` and `XXX` comments in any language that uses `#`, `//`, `/* */`, `<!-- -->`, `--` or `;` comments, reports the file and line, and counts them by tag.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python todo_comment_finder.py [FOLDER] [--tags TODO FIXME ...] [--owner NAME]
```
`--owner` keeps only comments written like `TODO(ada): ...`.

## Example
```bash
python todo_comment_finder.py demo-project
```
```
src/app.js:2  TODO  add rate limiting to the API
src/app.js:4  FIXME  crashes when the cart is empty
src/app.js:7  HACK  temporary workaround for the legacy client
src/utils.js:1  TODO (ada)  cache the results of this lookup
src/utils.js:3  XXX  remove before the 2.0 release
tests/app.test.js:2  TODO  cover the empty cart case
6 comment(s) found: 3 TODO, 1 FIXME, 1 HACK, 1 XXX.
```

## Notes
- Matching ignores letter case, but the tag must sit inside a comment, so strings containing the word TODO are not reported.
- `.git`, `node_modules`, virtual environments, build folders, binary files and files over 1 MB are skipped.
- Read-only.
