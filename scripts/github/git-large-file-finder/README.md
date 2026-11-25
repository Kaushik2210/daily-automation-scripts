# git-large-file-finder

## Purpose
Find the biggest files across a repository's entire history, including files that were deleted
long ago but still make every clone heavy. Marks which ones are gone from the latest commit.

## Install
No dependencies beyond Python 3.11+ and `git`.

## Usage
```
python git_large_file_finder.py                        # this repo, files of 1M or more
python git_large_file_finder.py --min-size 500k --top 50
python git_large_file_finder.py --only-removed         # history-only bloat
python git_large_file_finder.py --fail-over 5M         # CI guard for the latest commit
python git_large_file_finder.py --format json
python git_large_file_finder.py --from-file objects.txt
```

`objects.txt` can be made with:
`git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)'`

It only reads the repository and never changes it. For removals it prints a
`git filter-repo` command for you to run yourself, since that rewrites history.

## Example
`--from-file git-objects.txt --min-size 1M`

```
4 file(s) at or above 1.0 MB, biggest first:

    46.0 MB  data/export-2025.csv  (2 versions)
    12.0 MB  assets/demo-video.mp4
     5.0 MB  build/app.zip
     1.2 MB  docs/manual.pdf
```

## Notes
- A file stored under several names is counted once.
- Exit code 1 means `--fail-over` found a file in the latest commit above the limit, or git failed.
- Without git (like the browser demo) the "removed" marker isn't available.
