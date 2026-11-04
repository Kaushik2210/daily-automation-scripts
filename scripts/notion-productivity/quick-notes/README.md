# quick-notes

## Purpose
Jot something down without leaving the terminal, then find it again. Add `#tags` inside a note and filter by them later.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python quick_notes.py add TEXT...            # e.g. add Buy oat milk #errands
python quick_notes.py list [--tag TAG]
python quick_notes.py search WORD [--tag TAG]
python quick_notes.py tags
python quick_notes.py delete NUMBER
```
Notes are stored in a small JSON file (default `~/.quick-notes.json`, change it with `--file`). That file is the tool's own storage, so changes are saved straight away.

## Example
```bash
python quick_notes.py list --tag errands --file notes.json
```
```
#3   2026-01-06 11:03  Call the bank about the card #errands #money
#1   2026-01-05 09:10  Buy oat milk #errands
2 note(s).
```

## Notes
- Newest notes come first. Note numbers are never reused.
- A tag is `#` followed by letters, digits, `_` or `-`; matching ignores case.
- `search` exits with 1 when nothing matches.
