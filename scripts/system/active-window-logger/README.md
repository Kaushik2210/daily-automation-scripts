# active-window-logger

## Purpose
Record which application you are using and for how long, as raw material for a screen-time report or a timesheet. The tool checks the focused window every couple of seconds and writes a CSV row (`time,app,title`) each time the focus changes, such as switching from your editor to the browser. A log like this feeds `screen-time-report`, which adds up the time per application.

## Install
Standard library only, Python 3.11+. Platform support:
- **Windows:** works out of the box (uses the Windows API).
- **macOS:** uses `osascript`; allow your terminal under System Settings > Privacy & Security > Accessibility to read window titles.
- **Linux:** needs `xdotool` and an X11 session (Wayland doesn't allow reading the active window).

## Usage
```bash
python active_window_logger.py watch [--log FILE] [--interval 2] [--seconds 3600] [--count 50] [--no-titles]
python active_window_logger.py show [--last 15]
```
`watch` runs until you press Ctrl-C (or `--seconds` / `--count` is reached) and appends to `window-log.csv` in your home folder unless you pass `--log`. `--no-titles` records only the application name, which is more private because window titles can contain document names, email subjects and web page titles. `show` prints the latest rows.

## Example
```bash
python active_window_logger.py show --log window-log.csv --last 8
```
```
2026-11-20 17:30:00  LockApp        Lock screen
2026-11-21 09:00:00  Chrome         Inbox - Mail
2026-11-21 09:20:00  Code           main.py - project
2026-11-21 10:15:00  Terminal       git status
2026-11-21 10:20:00  Code           main.py - project
2026-11-21 11:05:00  Slack          #team-chat
2026-11-21 11:20:00  Chrome         Docs - API reference
2026-11-21 12:00:00  LockApp        Lock screen

Showing 8 of 23 logged window change(s).
```

## Notes
- The log is plain text and may contain sensitive titles; keep it private or use `--no-titles`.
- Only changes are logged, so the file stays small. A long gap between rows usually means the computer was idle or locked.
- The website demo shows a saved log; logging the live window works on your own computer.
