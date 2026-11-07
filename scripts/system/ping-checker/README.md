# ping-checker

## Purpose
Keep an eye on your connection. It pings one or more hosts, summarises replies, packet loss and response times (min, average, max) and can log every check to a CSV so you can see when things got slow. It also reads saved ping output from Linux, macOS or Windows.

## Install
Standard library only, Python 3.11+. It uses your system's `ping` command.

## Usage
```bash
python ping_checker.py HOST [HOST ...] [-c COUNT] [--log pings.csv]
python ping_checker.py --parse ping-output.txt
```
Run it on a schedule (cron or Windows Task Scheduler) with `--log` to build up a history. The exit code is 1 if any host sent no replies at all. Host names are validated before anything is run, and nothing goes through a shell.

## Example
```bash
python ping_checker.py --parse ping.txt
```
```
example.com              4/5 replies, 20% loss, min 11.9 / avg 21.1 / max 48.2 ms
```

## Notes
- Pinging needs a real network and the `ping` program, so the website demo can only analyse saved output with `--parse`.
- Some networks block ping; "no replies" doesn't always mean the host is down.
- The CSV has the columns `timestamp, host, sent, received, loss_percent, min_ms, avg_ms, max_ms`.
