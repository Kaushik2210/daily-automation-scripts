# event-log-exporter

## Purpose
Export recent system events, with errors and warnings by default, to a CSV, JSON or text file you
can attach to a bug report, search, or keep as a record. It reads journald on Linux, the Windows
Event Log (System and Application) and the unified log on macOS, and gives every event the same
columns: `time`, `level`, `source`, `id`, `message`.

## Install
No dependencies beyond Python 3.11+. It uses `journalctl`, PowerShell or `log` depending on the
system.

## Usage
```
python event_log_exporter.py --output events.csv                  # last 24 hours, warnings and errors
python event_log_exporter.py --hours 6 --level error --format json --output errors.json
python event_log_exporter.py --source nginx --contains timeout --format text
python event_log_exporter.py --level info --limit 5000 --format jsonl --output all.jsonl
python event_log_exporter.py --from-file saved-journal.jsonl
```

- `--level` is the lowest level to include: `info`, `warning` (default) or `error`.
- `--output` writes a new file and refuses to overwrite one unless you add `--force`.
- Messages are tidied onto one line. A one-line summary (counts per level and the busiest sources)
  is printed after the export.
- `--from-file` reads saved `journalctl -o json`, `Get-WinEvent | ConvertTo-Json` or
  `log show --style ndjson` output, so you can filter an export that someone sent you.

## Example
`--from-file journal-events.jsonl --level error --format text`

```
2026-11-24T03:07:00Z  ERROR   cron.service: I/O error, dev sda, sector 4096
2026-11-24T03:28:00Z  ERROR   sshd.service: I/O error, dev sda, sector 4096
2026-11-24T03:44:00Z  ERROR   cron.service: I/O error, dev sda, sector 4096
2026-11-24T04:32:00Z  ERROR   nginx.service: I/O error, dev sda, sector 4096
2026-11-24T05:36:00Z  ERROR   systemd: Failed to start Redis service
2026-11-24T06:49:00Z  ERROR   sshd.service: I/O error, dev sda, sector 4096
2026-11-24T08:11:00Z  ERROR   cron.service: Failed to start Redis service
2026-11-24T09:52:00Z  ERROR   cron.service: Failed to start Redis service
2026-11-24T10:14:00Z  ERROR   cron.service: Failed to start Redis service
2026-11-24T11:00:00Z  ERROR   sshd.service: Failed to start Redis service

10 event(s): 10 error; top sources: cron.service (5), sshd.service (3), nginx.service (1)
```

## Notes
- Reading the Windows Security log or some journal entries may need administrator or `sudo`
  rights; this tool only asks for System and Application events.
- System logs can contain usernames, hostnames and IP addresses, so check an export before sharing.
- On Windows, events with no text message are exported with an empty message.
