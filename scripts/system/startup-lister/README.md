# startup-lister

## Purpose
List every program that starts automatically with your OS, so you can see what slows down your
login or runs without you knowing. It flags disabled entries and ones that run from a temp or
downloads folder, which is unusual for something legitimate.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python startup_lister.py
python startup_lister.py --only-enabled
python startup_lister.py --format csv > startup.csv
python startup_lister.py --root ~/backup-of-home        # scan a copy of a home folder
```

What it looks at:

| System | Places |
|---|---|
| Windows | the `Run` and `RunOnce` registry keys (user and machine) and the Startup folders |
| macOS | `~/Library/LaunchAgents`, `/Library/LaunchAgents` and `/Library/LaunchDaemons` |
| Linux | `~/.config/autostart` and `/etc/xdg/autostart` |

It only reads; it never disables or removes anything. To turn an entry off, use your system's own
tool (Task Manager's Startup tab, `launchctl unload`, or your desktop's Startup Applications).

## Example
`--root startup-demo`

```
autostart (desktop) (3)
  Dropbox: dropbox start -i
  Old Tool: /opt/old/tool  [disabled]
  Slack: /usr/bin/slack --startup

launchd agent (2)
  com.example.manual: /usr/local/bin/manual  [disabled]
  com.example.sync: /usr/local/bin/sync --daemon

startup folder (1)
  OneDrive: startup-demo\Startup\OneDrive.cmd

6 item(s), 4 enabled, 2 disabled.
```

## Notes
- A launchd entry only counts as enabled if it has `RunAtLoad` or `KeepAlive`.
- Linux autostart entries with `Hidden=true` or `X-GNOME-Autostart-enabled=false` show as
  disabled.
- Windows services and scheduled tasks that start at boot are not covered; use
  `service-status-checker` for services.
