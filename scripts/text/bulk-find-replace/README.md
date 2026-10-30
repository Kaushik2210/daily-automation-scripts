# bulk-find-replace

## Purpose
Replace a word, phrase or regex across every matching file in a folder, after checking exactly what would change.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python bulk_find_replace.py FOLDER --find TEXT [--replace TEXT] [--pattern GLOB]
                            [--regex] [-i] [--apply]
```
Dry run by default; pass `--apply` to write the changes.

## Example
```bash
python bulk_find_replace.py ./docs --find "Acme Ltd" --replace "Acme Inc" --pattern "*.md"
```
```
docs/about.md: 3 replacement(s)
docs/contact.md: 1 replacement(s)
Would replace 4 occurrence(s) in 2 file(s). Use --apply to do it.
```

## Notes
- Searches subfolders. Files that aren't valid UTF-8 text are skipped.
- Without `--regex` the search text is matched literally, including dots and brackets.
- With `--regex` you can use groups in the replacement, e.g. `\1`.
