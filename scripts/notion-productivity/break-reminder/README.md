# break-reminder

## Purpose
Long stretches at a screen are hard on your back and eyes. This prints a gentle reminder in your terminal every half hour (or whatever you choose), with a different tip each time. There is no desktop app to install.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python break_reminder.py [--every MIN] [--total MIN] [--message TEXT]
                         [--plan] [--start HH:MM] [--unit minutes|seconds] [--no-bell]
```
Run it in a spare terminal tab. `--plan` lists the reminder times and exits. `--unit seconds` makes the interval seconds for a quick demo. Press Ctrl+C to stop.

## Example
```bash
python break_reminder.py --plan --start 09:00 --every 45 --total 180
```
```
09:45  Stand up and stretch your legs.
10:30  Drink some water.
11:15  Look at something 20 feet away for 20 seconds.
12:00  Roll your shoulders and unclench your jaw.
4 reminder(s) over 180 minutes, every 45 minutes.
```

## Notes
- Reminders start one interval after the start time and stop after `--total` minutes.
- Without `--message` the five built-in tips rotate; with it, your text repeats.
- The bell may be muted by your terminal settings; add `--no-bell` to silence it.
