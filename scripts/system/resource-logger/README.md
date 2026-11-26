# resource-logger

## Purpose
Record CPU, memory and disk use to a CSV file at a fixed interval, so you can see what a machine
was doing overnight or while a job ran. Open the CSV in a spreadsheet, or chart it with
`chart-generator`.

## Install
No dependencies beyond Python 3.11+. On Windows it asks PowerShell for CPU and memory, on macOS it
reads `top` and `vm_stat`, and on Linux it reads `/proc`.

## Usage
```
python resource_logger.py --interval 5 --count 12
python resource_logger.py --output usage.csv --interval 60 --count 1440     # one day, per minute
python resource_logger.py --output usage.csv --append --interval 60 --count 60
python resource_logger.py --disk D:\ --quiet --output usage.csv
```

- `--output` creates a new CSV with a header row. An existing file is never overwritten; add
  `--append` to keep adding rows to it (the header is written only once).
- Each row is flushed to disk as it is written, so you lose nothing if you stop it with Ctrl+C.
- A min/avg/max summary is printed at the end.
- `--simulate` produces repeatable fake readings (use `--start` for the first timestamp). It's for
  demos and for trying out charts without a real machine.

## Example
`--simulate --count 6 --interval 60 --start 2026-11-26T09:00:00`

```
2026-11-26T09:00:00  cpu  22.8%  mem  55.0% (8922 MB)  disk  71.2% (142.3 GB free)
2026-11-26T09:01:00  cpu   9.0%  mem  56.5% (9009 MB)  disk  71.3% (142.3 GB free)
2026-11-26T09:02:00  cpu   8.2%  mem  57.1% (9093 MB)  disk  71.4% (142.3 GB free)
2026-11-26T09:03:00  cpu  58.9%  mem  56.9% (9207 MB)  disk  71.4% (142.3 GB free)
2026-11-26T09:04:00  cpu  28.3%  mem  59.2% (9320 MB)  disk  71.5% (142.3 GB free)
2026-11-26T09:05:00  cpu  17.3%  mem  59.5% (9496 MB)  disk  71.5% (142.3 GB free)

cpu     min   8.2  avg  24.1  max  58.9
memory  min  55.0  avg  57.4  max  59.5
disk    min  71.2  avg  71.4  max  71.5
```

## Notes
- CPU % is the whole machine's busy time between samples. On Linux the first reading waits a
  quarter of a second to get a baseline.
- Memory used excludes cache that can be freed (Linux `MemAvailable`).
- CSV columns: `time`, `cpu_percent`, `memory_percent`, `memory_used_mb`, `disk_percent`,
  `disk_free_gb`.
