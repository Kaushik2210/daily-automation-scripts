# task-scheduler-helper

## Purpose
Turn "run this command every weekday at 08:30" into ready-to-paste entries for the system's
scheduler: a crontab line, a Windows Task Scheduler (`schtasks`) command, a macOS launchd plist, or
systemd service and timer files. You don't need to remember each system's syntax.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python task_scheduler_helper.py --command "python backup.py" --every daily --at 02:30
python task_scheduler_helper.py --command "python sync.py" --every 15m --target cron
python task_scheduler_helper.py --command "python report.py" --every weekly --days mon,fri --at 08:00
python task_scheduler_helper.py --command "python report.py" --every monthly --day-of-month 1 --target all
python task_scheduler_helper.py --command "python backup.py" --log ~/backup.log --name nightly-backup
```

- `--every` takes `15m`, `2h`, `hourly`, `daily`, `weekly` or `monthly`. Use `--at HH:MM` for the
  time of day, `--days mon,wed,fri` for weekly and `--day-of-month 1-28` for monthly.
- `--target` picks `cron`, `schtasks`, `launchd` or `systemd`; the default is the right one for this
  system and `all` prints all four.
- `--log FILE` appends the command's output to that file.
- It only prints text. Nothing is installed, so you can read it first and then paste or save it.

## Example
`--command "python C:/scripts/backup.py --apply" --name nightly-backup --every weekly --days mon,wed,fri --at 02:30 --target all`

```
Schedule: every Mon, Wed, Fri at 02:30
Nothing has been installed; copy what you need.

============ cron ============
# Add with: crontab -e   (list with: crontab -l)
30 2 * * MON,WED,FRI python C:/scripts/backup.py --apply

============ schtasks ============
REM Run in a Command Prompt. Remove later with: schtasks /Delete /TN "nightly-backup"
schtasks /Create /TN "nightly-backup" /TR "python C:/scripts/backup.py --apply" /SC WEEKLY /D MON,WED,FRI /ST 02:30 /F

============ launchd ============
# Save as ~/Library/LaunchAgents/com.user.nightly-backup.plist, then: launchctl load ~/Library/LaunchAgents/com.user.nightly-backup.plist
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.user.nightly-backup</string>
  <key>ProgramArguments</key>
  <array>
    <string>python</string>
    <string>C:/scripts/backup.py</string>
    <string>--apply</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>2</integer><key>Minute</key><integer>30</integer><key>Weekday</key><integer>1</integer></dict>
    <dict><key>Hour</key><integer>2</integer><key>Minute</key><integer>30</integer><key>Weekday</key><integer>3</integer></dict>
    <dict><key>Hour</key><integer>2</integer><key>Minute</key><integer>30</integer><key>Weekday</key><integer>5</integer></dict>
  </array>
</dict>
</plist>

============ systemd ============
# Save as ~/.config/systemd/user/nightly-backup.service
[Unit]
Description=nightly-backup

[Service]
Type=oneshot
ExecStart=python C:/scripts/backup.py --apply

# Save as ~/.config/systemd/user/nightly-backup.timer
[Unit]
Description=Run nightly-backup

[Timer]
OnCalendar=Mon,Wed,Fri *-*-* 02:30:00
Persistent=true

[Install]
WantedBy=timers.target

# Then: systemctl --user daemon-reload && systemctl --user enable --now nightly-backup.timer
```

## Notes
- Monthly days are limited to 1-28 so the task runs in every month, including February.
- Use full paths in commands: schedulers don't start in your usual folder or with your usual PATH.
- launchd calls Sunday 0 and Monday 1; the generated plist already takes care of that.
