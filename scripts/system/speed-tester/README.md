# speed-tester

## Purpose
Measure your download speed by fetching a test file and timing it. It shows each run, the time to
the first byte, and the average, median, best and worst speed. It can append every run to a CSV so
you can watch how your connection changes through the day.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python speed_tester.py                                  # 3 runs against a 25 MB test file
python speed_tester.py --runs 5 --max-seconds 10
python speed_tester.py --url https://example.com/100MB.bin --max-bytes 50000000
python speed_tester.py --log speed.csv --min-mbps 50     # exit 1 if the average is below 50
python speed_tester.py --from-file speed-runs.txt
```

- The default file is a public 25 MB test file from Cloudflare. Use `--url` for your own server.
  Only `http://` and `https://` addresses are accepted.
- `--max-bytes` and `--max-seconds` stop a run early, so slow links don't download for ages.
- `--log` appends rows (`time,url,bytes,seconds,mbps`) to a CSV and writes the header once.
- `--from-file` summarises saved `bytes seconds` lines without any network access.

## Example
`--from-file speed-runs.txt`

```
1.   25.0 MB in  2.31 s =    86.6 Mbit/s   10.8 MB/s
  2.   25.0 MB in  2.05 s =    97.6 Mbit/s   12.2 MB/s
  3.   25.0 MB in  3.40 s =    58.8 Mbit/s    7.4 MB/s
  4.   25.0 MB in  2.18 s =    91.7 Mbit/s   11.5 MB/s

4 run(s): average 83.7 Mbit/s, median 89.2, best 97.6, worst 58.8
```

## Notes
- Speeds are in megabits per second (1 Mbit/s = 125,000 bytes per second), the way providers
  quote them. The MB/s column is megabytes per second.
- This measures one connection to one server, so results vary with the server and the time of day.
- The browser demo can only summarise saved timings; it can't download.
