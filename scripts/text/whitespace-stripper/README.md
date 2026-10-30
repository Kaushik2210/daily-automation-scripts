# whitespace-stripper

## Purpose
Remove trailing spaces and tabs, drop blank lines at the end of a file, and make line endings consistent. Handy before committing text, markdown or notes.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python whitespace_stripper.py PATH [PATH ...] [--pattern GLOB] [--eol keep|lf|crlf]
                              [--no-final-newline] [--apply]
```
Folders are searched recursively for files matching `--pattern` (default `*.txt`). Dry run by default; pass `--apply` to rewrite files.

## Example
```bash
python whitespace_stripper.py ./notes --pattern "*.md" --eol lf
```
```
notes/todo.md
notes/ideas.md
Would clean 2 file(s). Use --apply to do it.
```

## Notes
- By default the file keeps whichever line ending it mostly uses.
- Files that aren't valid UTF-8 are skipped, never rewritten.
- Files already clean are not listed and not touched.
