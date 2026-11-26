# process-monitor

## Purpose
Watch the CPU and memory use of the processes you care about. Processes are grouped by name, so
twelve `chrome` helpers show up as one line with a count, a total memory figure and a CPU %.

## Install
No dependencies beyond Python 3.11+. It uses `ps` on Linux and macOS and PowerShell on Windows.

## Usage
```
python process_monitor.py                       # everything, sorted by CPU
python process_monitor.py chrome python         # names match as substrings, or use patterns
python process_monitor.py "nginx*" --interval 5 --count 12
python process_monitor.py postgres --cpu-over 80 --mem-over 2000
python process_monitor.py --format csv > snapshot.csv
```

- `CPU %` is measured between two samples `--interval` seconds apart; 100 means one full core.
- `--cpu-over` and `--mem-over` (MB) print `ALERT` lines and make the exit code 1, which is handy
  in a cron job or a script.
- `--from-file` reads a saved `ps -axo pid=,etime=,cputime=,rss=,comm=` listing. That is a single
  snapshot, so it shows total CPU time and memory instead of CPU %.

## Example
`--from-file ps-snapshot.txt chrome nginx python node`

```
process  count   memory MB   CPU time
python       1      1806.6    1:55:00
chrome       3       996.1    2:39:21
node         2       502.9    0:16:14
nginx        4       156.2    0:36:57
```

## Notes
- Names are the program name only (no path or arguments).
- On Windows the memory figure is the working set; on Linux and macOS it is resident memory.
- Short-lived processes that start and end between two samples are not counted.
