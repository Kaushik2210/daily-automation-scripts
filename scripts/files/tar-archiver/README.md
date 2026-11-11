# tar-archiver

## Purpose
Make compressed tar archives you can check later. The tool bundles folders and files into a `.tar.gz`, `.tar.bz2`, `.tar.xz` or plain `.tar`, and puts a `MANIFEST.json` first inside it listing every file with its size and SHA-256 hash. Months later, `verify` re-reads the archive and tells you whether any file is damaged or missing. Unlike zip, tar keeps Unix permissions and timestamps, but the owner and group names are removed so nothing private is stored.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python tar_archiver.py create FOLDER [FOLDER_OR_FILE ...] --out backup.tar.gz [--exclude PATTERN ...] [--apply]
python tar_archiver.py list backup.tar.gz
python tar_archiver.py verify backup.tar.gz
```
The compression follows the extension you give `--out` (`.tar.gz`/`.tgz`, `.tar.bz2`, `.tar.xz` or `.tar`). Folders are stored under their own name. `create` only shows what it would do until you add `--apply`; the archive is built under a temporary name and renamed when complete, and an existing file is never overwritten. `list` prints the manifest, and `verify` exits with 1 if any file is missing or damaged. Symbolic links are skipped, and an archive created inside a folder it archives leaves itself out.

## Example
```bash
python tar_archiver.py create demo-project --out demo.tar.gz --exclude "*.md"
```
```
5 file(s), 723 B -> demo.tar.gz (plus MANIFEST.json)
  would add demo-project/LICENSE
  would add demo-project/package.json
  would add demo-project/src/app.js
  would add demo-project/src/utils.js
  would add demo-project/tests/app.test.js

Dry run - no archive created. Add --apply to create it.
```

## Notes
- Add `--apply` to create the archive. Without it nothing is written.
- Pair it with `backup-rotator` to keep only the newest archives.
- `verify` checks integrity against the manifest; it can't tell whether the original files were right to begin with.
- On the website demo the archive is created in your browser's temporary folder.
