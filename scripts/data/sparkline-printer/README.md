# sparkline-printer

## Purpose
Print compact sparklines, tiny one-line charts, for a list of numbers, a text file or CSV columns.
Handy in terminal dashboards, logs, commit messages and reports.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python sparkline_printer.py 3 7 4 9 12 8 15
python sparkline_printer.py --from-file latencies.txt --stats
python sparkline_printer.py --csv sales.csv --column revenue --column costs --stats
python sparkline_printer.py --from-file big.txt --width 40 --min 0 --max 100
```

- Each series is scaled between its own lowest and highest value. `--min` and `--max` fix the scale
  so several lines can be compared fairly.
- `--width` averages long series down to that many characters.
- `--stats` adds the min, max, last value and the percentage change from the first value.
- `--style auto` uses block characters when the terminal can show them and plain ASCII otherwise.

## Example
`--csv sales-monthly.csv --column revenue --column costs --stats --style unicode`

```
revenue  ▁▂▃▄▅▆▆▆▅▆▇█  min 8,928  max 14,171  last 14,171 (+58.7%)
costs    ▂▁▃▃▆██▆▄██▇  min 5,317  max 8,911  last 8,576 (+49.2%)
```

## Notes
- A flat series is drawn at mid height.
- In CSV columns, blank or non-numeric cells are skipped. Thousands separators are understood.
