# service-status-checker

## Purpose
Check whether named services are running. It works with systemd on Linux, Windows services and
launchd on macOS, and exits with 1 if any service isn't in the state you expect, so it is easy to
use from a script, a cron job or a health check.

## Install
No dependencies beyond Python 3.11+. It uses `systemctl`, `sc` or `launchctl`, whichever your
system has.

## Usage
```
python service_status_checker.py nginx postgresql
python service_status_checker.py "print spooler" w32time       # Windows display names work too
python service_status_checker.py docker --expect stopped
python service_status_checker.py --list                       # everything found
python service_status_checker.py nginx --format json
python service_status_checker.py nginx --from-file services.txt
```

- A name matches exactly first (with or without `.service`), then the display name, then as part of
  either.
- States are `running`, `stopped`, `failed`, or the system's own word (for example
  `start pending`). Services that are not found count as a failure.
- `--from-file` reads saved `systemctl list-units --type=service --all --no-legend --plain`,
  `sc query state= all` or `launchctl list` output.

## Example
`--from-file services-systemctl.txt nginx redis docker cron --list`

```
OK   nginx: running (active/running)
FAIL redis-server: failed (failed/failed)
FAIL docker: stopped (inactive/dead)
OK   cron: running (active/running)
  redis-server  failed    Advanced key-value store
  cron          running   Regular background program processing
  nginx         running   A high performance web server
  postgresql    running   PostgreSQL database server
  ssh           running   OpenBSD Secure Shell server
  docker        stopped   Docker Application Container Engine

2 of 4 as expected (running).
```

## Notes
- It only reads service state. It never starts or stops anything.
- Windows `sc query` can take a few seconds on a busy machine.
