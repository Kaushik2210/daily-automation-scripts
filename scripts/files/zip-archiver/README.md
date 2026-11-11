# zip-archiver

## Purpose
Zip up a project without the clutter. Give it one or more folders (or files) and it builds a standard `.zip` that opens everywhere, leaving out whatever you exclude: build output, logs, `node_modules`, version-control folders and so on. By default it only shows what would go in; the archive is built under a temporary name and renamed when complete, so a failed run never leaves a broken zip.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python zip_archiver.py FOLDER [FOLDER_OR_FILE ...] --out archive.zip [--exclude PATTERN ...] [--exclude-common] [--apply]
```
`--exclude` takes names or patterns such as `build`, `*.log` or `docs/private/*` (repeat for several). `--exclude-common` adds `.git`, `node_modules`, `__pycache__`, `*.pyc`, `.venv`, `.idea`, `.DS_Store` and `Thumbs.db`. Folders are stored under their own name inside the zip; `--no-top-folder` puts their contents at the top instead. `--level 1-9` trades speed for size (6 by default). Symbolic links are skipped, and an archive created inside the folder it zips is left out of itself. An existing file is never overwritten.

## Example
```bash
python zip_archiver.py demo-project --out demo.zip --exclude "*.md" --exclude LICENSE
```
```
4 file(s), 681 B -> demo.zip
  would add demo-project/package.json
  would add demo-project/src/app.js
  would add demo-project/src/utils.js
  would add demo-project/tests/app.test.js

Dry run - no zip created. Add --apply to create it.
```

## Notes
- Add `--apply` to create the zip. Without it nothing is written.
- Pair it with `backup-rotator` to keep only the newest archives, and `backup-verifier` to check one against its source.
- Zips don't keep Unix permissions on every platform; use `tar-archiver` if you need that.
- On the website demo the zip is created in your browser's temporary folder.
