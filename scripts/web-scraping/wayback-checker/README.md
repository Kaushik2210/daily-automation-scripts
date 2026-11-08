# wayback-checker

## Purpose
Check whether the Internet Archive has a copy of a page. Give it URLs (or a text file full of them) and it asks the Wayback Machine's public availability API for the closest saved snapshot, printing the date and a link you can open. It's handy for rescuing dead links, citing sources and checking what a page used to say.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python wayback_checker.py URL [URL ...] [--file urls.txt] [--timestamp 20200101] [--delay 1]
python wayback_checker.py --response saved-lookups.json
```
`--timestamp` asks for the snapshot closest to a date. Lookups are spaced `--delay` seconds apart to be kind to the free service. `--response` reads availability responses you saved earlier (one JSON object, or a list of them) without touching the network. The exit code is 1 if any URL has no snapshot.

## Example
```bash
python wayback_checker.py --response wayback.json
```
```
example.com: 2024-01-15 08:30 UTC  https://web.archive.org/web/20240115083000/http://example.com/
gone.example.net: no snapshot saved
1 of 2 URL(s) have a snapshot.
```

## Notes
- The tool only reads from the public API; it doesn't ask the Archive to save anything.
- A snapshot may be days or years from the date you asked for. Check the date in the output.
- The website demo only reads saved responses; live lookups work on your own computer.
