# page-change-detector

## Purpose
Find out when a web page changes without staring at it. The tool reduces a page to its visible text, remembers the last version, and tells you which lines were added or removed the next time you run it. The exit code is 1 when something changed, so it slots straight into cron, Task Scheduler or a shell `if`.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python page_change_detector.py SOURCE --state last-seen.json [--ignore REGEX] [--no-update]
python page_change_detector.py SOURCE --previous old-copy.html
```
With `--state` the first run saves a baseline and later runs compare against it, then store the new version. `--no-update` keeps the old baseline so you're told about the change every time until you accept it. `--previous` compares with a saved page and writes nothing. Use `--ignore` for text that always changes, such as `Visitors: \d+`.

## Example
```bash
python page_change_detector.py jobs.html --previous jobs-old.html
```
```
CHANGED: 2 line(s) added, 1 removed.
  - Summer Intern - London
  + Product Designer - Berlin
  + Data Analyst - London
```

## Notes
- Only visible text is compared. Changes to scripts, styles and markup don't count.
- Exit codes: 0 means no change (or a new baseline), 1 means the page changed or couldn't be checked.
- Be kind to the sites you watch: check every few hours, not every few seconds.
- On the website demo only saved files can be compared; watching a URL works on your own computer.
