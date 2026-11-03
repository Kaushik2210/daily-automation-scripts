# screenshot-organizer

## Purpose
Clear a desktop or downloads folder full of screenshots by filing them into `YEAR/YEAR-MONTH` folders. The date comes from the file name when it contains one (as macOS, Windows and Android screenshots do), and from the modified time otherwise.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python screenshot_organizer.py [FOLDER] [--pattern REGEX] [--layout year-month|month] [--apply]
```
Dry run by default; pass `--apply` to move the files. A file counts as a screenshot when it is an image whose name matches `--pattern` (default: screenshot, screen shot, snip or capture).

## Example
```bash
python screenshot_organizer.py ~/Desktop
```
```
Screenshot 2026-03-01 at 09.30.15.png -> 2026/2026-03/
Screenshot 2026-03-02 at 14.05.00.png -> 2026/2026-03/
Would move 2 screenshot(s). Use --apply to do it.
```

## Notes
- Only files directly inside the folder are moved; other images are left alone.
- A file is skipped if the destination already has one with the same name.
- Recognised date formats: `2026-03-01`, `2026_03_01`, `2026.03.01` and `20260301`.
