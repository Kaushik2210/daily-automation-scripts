# pomodoro-timer

## Purpose
Work in focused bursts with a countdown in your terminal: 25 minutes of focus, a short break, and a longer break after four sessions. Every phase ends with a terminal bell.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python pomodoro_timer.py [--focus MIN] [--break MIN] [--long-break MIN] [--sessions N]
                         [--rounds N] [--unit minutes|seconds] [--plan] [--start HH:MM] [--no-bell]
```
Run it with no options for the classic 25/5/15 cycle. `--plan` prints the schedule with clock times and exits, which is useful for planning your day. `--unit seconds` shrinks every duration to seconds for a quick demo. Press Ctrl+C to stop.

## Example
```bash
python pomodoro_timer.py --plan --start 09:00
```
```
09:00  Focus 1/4    25 min
09:25  Short break  5 min
09:30  Focus 2/4    25 min
09:55  Short break  5 min
10:00  Focus 3/4    25 min
10:25  Short break  5 min
10:30  Focus 4/4    25 min
10:55  Long break   15 min
Ends at 11:10. 100 minutes of focus in 8 phases.
```

## Notes
- The countdown updates in place on one line and needs a real terminal; on the website use `--plan`.
- The final focus session of a round is followed by the long break.
- Use `--no-bell` if the sound is unwelcome.
