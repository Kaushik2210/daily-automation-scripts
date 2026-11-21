# wallpaper-rotator

## Purpose
Keep your desktop fresh by cycling through a folder of pictures. Run it by hand or from a scheduler (Task Scheduler, cron, launchd) and it picks the next picture and sets it as your wallpaper. Three modes: **next** goes through the folder in order and starts over, **random** picks a different picture each time, and **daily** shows one picture per day (the same all day).

## Install
Standard library only, Python 3.11+. Setting the wallpaper uses the operating system:
- **Windows:** built in (png, jpg and bmp).
- **macOS:** built in (uses `osascript`).
- **Linux:** needs GNOME's `gsettings` (also sets the dark-mode picture) or `feh`.

## Usage
```bash
python wallpaper_rotator.py FOLDER [--mode next|random|daily] [--seed N] [--state FILE] [--apply]
```
Dry run by default: it shows which picture is next and what it would run, and changes nothing. With `--apply` it sets the wallpaper and remembers the picture in a small state file (`.wallpaper-rotator.json` in your home folder, or `--state`) so `next` continues from there. `--seed` makes random choices repeatable. Supported files: `.png`, `.jpg`, `.jpeg`, `.bmp`.

## Example
```bash
python wallpaper_rotator.py wallpapers/
```
```
{{OUTPUT}}
```

## Notes
- Original pictures are never modified.
- To rotate every hour on Windows, create a Task Scheduler task that runs `python wallpaper_rotator.py FOLDER --apply`.
- The website demo can only show the plan; changing the real wallpaper works on your own computer.
