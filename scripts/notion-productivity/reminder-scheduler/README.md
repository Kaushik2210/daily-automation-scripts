# reminder-scheduler

## Purpose
Set quick reminders without opening any app. Tell it when and what ("25m  Stand up", "15:30  Submit the timesheet") and it waits in the terminal, then rings the terminal bell and prints the message. You can set one reminder from the command line, or load a whole day of them from a file. Handy for a Pomodoro, a meeting or "move the laundry".

## Install
Standard library only, Python 3.11+. Nothing to install. `--notify` additionally uses `osascript` (macOS), `notify-send` (Linux) or `msg` (Windows) if available.

## Usage
```bash
python reminder_scheduler.py 25m "Stand up and stretch"
python reminder_scheduler.py 15:30 "Submit the timesheet" [--notify]
python reminder_scheduler.py --file reminders.txt [--plan] [--now "2026-11-21 09:00"]
```
Times can be relative (`25m`, `1h30m`, `90s`, `in 2h`), a clock time today or tomorrow (`15:30`) or a full date (`2026-11-22 09:00`). A reminders file has one `when message` per line; blank lines and `#` comments are ignored. `--plan` prints the schedule without waiting. Keep the terminal window open while you wait; Ctrl-C cancels everything.

## Example
```bash
python reminder_scheduler.py --file reminders.txt --plan --now "2026-11-21 09:00"
```
```
4 reminder(s), starting 2026-11-21 09:00:00:
  Sat 21 Nov 09:25  (in 0h 25m)  Stand up and stretch
  Sat 21 Nov 10:00  (in 1h 00m)  Join the team call
  Sat 21 Nov 15:30  (in 6h 30m)  Submit the timesheet
  Sat 21 Nov 18:00  (in 9h 00m)  Go home!
Plan only; run without --plan to wait for them.
```

## Notes
- Reminders only live while the program runs; if you close the window or shut down, they are gone.
- A clock time that has already passed today means tomorrow at that time.
- Use `countdown-timer` for a simple countdown and `snippet-manager` for reusable text.
