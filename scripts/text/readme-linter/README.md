# readme-linter

## Purpose
Review a README the way a new visitor would. The linter checks for a title and a short description, install, usage, license and contributing sections, at least one code example, heading levels that don't skip, duplicate headings, empty links, leftover TODO text, a sensible length and a table of contents on long files. Each check is marked PASS, WARN or FAIL and the file gets a score out of 100.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python readme_linter.py README.md [--min-score 60]
```
The exit code is 1 when the score is below `--min-score` or any check FAILs, so it can guard a pull request. Headings inside code blocks are ignored.

## Example
```bash
python readme_linter.py README.md
```
```
README.md: score 55/100

  [PASS] Title: Demo Project
  [FAIL] No short description under the title (what is this and who is it for?)
  [PASS] Has the install section
  [PASS] Has the usage section
  [FAIL] Missing the license section
  [WARN] Missing the contributing section
  [WARN] Missing the features or overview section
  [WARN] No code blocks: show a command or snippet people can copy
  [PASS] Heading levels are in order
  [WARN] Duplicate headings: usage
  [PASS] No TODO/placeholder text
  [WARN] Only 13 words; most READMEs need more detail

2 problem(s), 5 suggestion(s).
```

## Notes
- Section names are matched loosely ("Getting started" counts as install, "Examples" as usage).
- A high score means the README is complete, not that it is well written; read it too.
- Use `markdown-link-checker` to verify the links in it.
