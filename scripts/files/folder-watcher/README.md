# folder-watcher

## Purpose
Automate "when a file lands here, do this". The tool watches a folder and, for every new (or changed) file, runs a command of your choice: convert a CSV, upload a report, resize a photo, start a backup. It waits until a file has stopped changing before acting, so it doesn't grab half-written files, and it ignores temporary files (`*.tmp`, `*.part`, `*.crdownload`, hidden files).

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python folder_watcher.py FOLDER --run "python process.py {path}" [--pattern "*.csv"] [--events new|changed|both]
                         [-r] [--include-existing] [--once] [--seconds N] [--interval 2] [--settle 2] [--apply]
```
Placeholders in `--run`: `{path}` (full path), `{name}`, `{stem}`, `{ext}` and `{dir}`. The command is split into words first and the file name is filled in afterwards, so names with spaces are safe and no shell is involved. **Dry run by default:** events and the commands that would run are printed; add `--apply` to really run them. By default only files that appear after the watch starts count; `--include-existing` also handles the files already there, and `--once` checks once and stops. Without `--once` it keeps watching until you press Ctrl-C (or `--seconds` runs out).

## Example
```bash
python folder_watcher.py incoming/ --run "python process.py {path}" --once --settle 0
```
```
Watching incoming for new '*' files (dry run: commands are only shown)...
new     notes.txt
  would run: python process.py incoming\notes.txt
new     orders.csv
  would run: python process.py incoming\orders.csv
new     report.pdf
  would run: python process.py incoming\report.pdf
3 event(s) handled. Use --apply to run the command.
```

## Notes
- It polls the folder every `--interval` seconds, so it needs no extra libraries and works the same on every system.
- A command's exit code is shown after each run; a failing command doesn't stop the watcher.
- Be careful what you run with `--apply`: the command receives whatever file arrives in the folder.
- Use `download-watcher` to sort a Downloads folder automatically.
