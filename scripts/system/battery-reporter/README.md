# battery-reporter

## Purpose
Report your battery's charge, status and health (how much capacity it has left compared with when
it was new), plus cycle count and an estimate of the time left. It can also log readings to a CSV
and summarise that history, so you can see how fast the battery is wearing out.

## Install
No dependencies beyond Python 3.11+. It reads `/sys/class/power_supply` on Linux, `ioreg` on macOS
and PowerShell plus `powercfg` on Windows.

## Usage
```
python battery_reporter.py
python battery_reporter.py --format json
python battery_reporter.py --log battery.csv           # run it daily from a scheduler
python battery_reporter.py --history battery.csv       # summarise the log
python battery_reporter.py --min-health 70             # exit 1 if the battery is worn out
python battery_reporter.py --sysfs ./power_supply      # read a saved Linux folder
```

- Health is the full-charge capacity as a percentage of the design capacity: 80% or more is good,
  60-80% is fair, below that is worn.
- The time left is only estimated while discharging, from the current draw.
- `--log` appends `time,percent,status,health` to a CSV (the header is written once). Use
  `task-scheduler-helper` to run it every day, then `--history` shows the trend.
- No battery, such as on a desktop, exits with 1 and a message.

## Example
`--sysfs battery-demo`

```
Charge:    74% (Discharging)
Health:    82.4% of design capacity (good)
Capacity:  41,200 now vs 50,000 when new (mWh or mAh)
Cycles:    312
Type:      Li-ion
Model:     SMP DELL 7XFMD
Draw:      8.4 W
Time left: 3.6 h
```

## Notes
- Windows builds a temporary battery report with `powercfg` to read the capacities; nothing is
  kept. If it isn't available you still get the charge and status.
- Numbers come from the battery's own firmware, so different laptops differ a little.
- The capacity unit (mWh or mAh) depends on the system; the ratio is what matters.
