# backup-size-estimator

## Purpose
Know what a backup will cost before you start it. The tool scans the folders you plan to back up and reports how many files there are, the total size, which folders and files are biggest, and which file types take the space. It estimates how small a compressed archive would be (text compresses a lot, photos and videos hardly at all) and, if you name a destination, checks it has enough free space. It only reads: nothing is copied or changed.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python backup_size_estimator.py FOLDER [FOLDER ...] [--exclude PATTERN ...] [--dest BACKUP_FOLDER] [--top 5]
```
`--exclude` takes names or patterns such as `node_modules` or `*.tmp`; the report says how much space the exclusions save, so you can try patterns until the size is sensible. With `--dest` the tool reads the free space of the drive that folder is on (even if the folder doesn't exist yet) and says whether the backup fits as a plain copy, only if compressed, or not at all; the exit code is 1 in the last case. Symbolic links are skipped.

## Example
```bash
python backup_size_estimator.py demo-project --exclude "*.md"
```
```
5 file(s) in 2 folder(s): 723 B
A plain copy needs about 723 B; a compressed archive about 199 B (a rough estimate).

Biggest folders:
       382 B  demo-project/src
       248 B  demo-project
        93 B  demo-project/tests

Biggest files:
       254 B  demo-project/src/app.js
       206 B  demo-project/package.json
       128 B  demo-project/src/utils.js
        93 B  demo-project/tests/app.test.js
        42 B  demo-project/LICENSE

By file type: .js 475 B, .json 206 B, (none) 42 B
```

## Notes
- The compressed estimate is a rule of thumb (about 25% for text and code, 100% for already-compressed formats such as JPEG, MP4 and ZIP, 70% for everything else). Real results vary.
- Free-space checks can't know about quotas, other programs writing at the same time or network drives that report oddly.
- Pair it with `backup-script`, `zip-archiver` or `tar-archiver` once the numbers look right.
