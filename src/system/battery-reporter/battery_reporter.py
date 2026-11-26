"""Report battery charge and health, and keep a simple charge history in a CSV."""
import argparse
import csv
import json
import platform
import re
import subprocess  # web-ok: used only on Windows and macOS to ask the system
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

DEFAULT_SYSFS = Path("/sys/class/power_supply")
HISTORY_FIELDS = ["time", "percent", "status", "health"]


def health_label(health):
    if health is None:
        return "unknown"
    return "good" if health >= 80 else "fair" if health >= 60 else "worn: consider a replacement"


def build(percent, status, design, full, cycles=None, technology=None, model=None, watts=None,
          now=None):
    """Assemble the report dict. design/full/now are in the same unit (mWh or mAh)."""
    health = round(full / design * 100, 1) if design and full else None
    hours = (round(now / (watts * 1000), 1) if now and watts and status == "Discharging"
             else None)
    return {"percent": percent, "status": status, "health_percent": health,
            "health": health_label(health), "design_capacity": design, "full_capacity": full,
            "cycles": cycles, "technology": technology, "model": model,
            "power_watts": watts, "hours_remaining": hours}


def read_sysfs(root):
    """Read the first BAT* folder of a /sys/class/power_supply layout."""
    root = Path(root)
    folders = sorted(p for p in root.glob("BAT*") if p.is_dir()) if root.is_dir() else []
    if not folders:
        return None

    def value(name):
        try:
            return (folders[0] / name).read_text(encoding="utf-8").strip()
        except OSError:
            return None

    def number(name):
        text = value(name)
        return int(text) if text and text.lstrip("-").isdigit() else None

    unit = "energy" if number("energy_full_design") else "charge"  # µWh or µAh
    full, design, now = number(f"{unit}_full"), number(f"{unit}_full_design"), number(f"{unit}_now")
    percent = number("capacity")
    if percent is None and full and now:
        percent = round(now / full * 100)
    power = number("power_now")
    return build(percent, value("status"), design and design // 1000, full and full // 1000,
                 number("cycle_count"), value("technology"),
                 " ".join(x for x in (value("manufacturer"), value("model_name")) if x) or None,
                 round(power / 1e6, 1) if power else None, now and now // 1000)


def parse_ioreg(text):
    """`ioreg -rn AppleSmartBattery` text (macOS)."""
    values = {k: v for k, v in re.findall(r'"(\w+)"\s*=\s*(\S+)', text)}
    if "MaxCapacity" not in values and "AppleRawMaxCapacity" not in values:
        return None

    def number(key):
        return int(values[key]) if values.get(key, "").lstrip("-").isdigit() else None

    full = number("AppleRawMaxCapacity") or number("MaxCapacity")
    design, current = number("DesignCapacity"), number("AppleRawCurrentCapacity")
    percent = number("CurrentCapacity")
    if percent is None and current and full:
        percent = round(current / full * 100)
    charging = values.get("IsCharging") == "Yes"
    plugged = values.get("ExternalConnected") == "Yes"
    status = "Charging" if charging else "Full" if plugged else "Discharging"
    return build(percent, status, design, full, number("CycleCount"))


def local(element):
    """An element's tag without its XML namespace."""
    return element.tag.rsplit("}", 1)[-1]


def parse_powercfg_xml(text, percent=None, status=None):
    """`powercfg /batteryreport /xml` output (Windows). Capacities are in mWh."""
    battery = next((e for e in ET.fromstring(text).iter() if local(e) == "Battery"), None)
    if battery is None:
        return None
    fields = {local(child): (child.text or "").strip() for child in battery}

    def number(name):
        return int(fields[name]) if fields.get(name, "").isdigit() else None

    return build(percent, status, number("DesignCapacity"), number("FullChargeCapacity"),
                 number("CycleCount"), None, fields.get("Manufacturer") or None)


def read_windows(run=subprocess.run):
    script = ("$b = Get-CimInstance Win32_Battery | Select-Object -First 1; "
              "if ($b) { ConvertTo-Json @($b.EstimatedChargeRemaining, $b.BatteryStatus) }")
    result = run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True,
                 timeout=60, check=False)
    if not result.stdout.strip():
        return None
    percent, code = json.loads(result.stdout)
    status = {1: "Discharging", 2: "Charging", 3: "Full", 6: "Charging", 7: "Charging"}.get(
        code, "Discharging")
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "battery.xml"
        run(["powercfg", "/batteryreport", "/output", str(target), "/xml"],
            capture_output=True, text=True, timeout=120, check=False)
        if not target.exists():
            return build(percent, status, None, None)
        return parse_powercfg_xml(target.read_text(encoding="utf-8"), percent, status)


def read_system(run=subprocess.run, system=None, sysfs=DEFAULT_SYSFS):
    system = system or platform.system()
    if system == "Windows":
        return read_windows(run)
    if system == "Darwin":
        result = run(["ioreg", "-rn", "AppleSmartBattery"], capture_output=True, text=True,
                     timeout=30, check=False)
        return parse_ioreg(result.stdout)
    return read_sysfs(sysfs)


def summarise_history(path):
    """Describe a history CSV: samples, charge range and how health has moved."""
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r.get("percent", "").strip().isdigit()]
    if not rows:
        raise ValueError("the history file has no readings")
    percents = [int(r["percent"]) for r in rows]
    lines = [f"History: {len(rows)} reading(s), {rows[0]['time'][:10]} to {rows[-1]['time'][:10]}",
             f"Charge:  lowest {min(percents)}%, highest {max(percents)}%, "
             f"average {sum(percents) / len(percents):.0f}%"]
    healths = [float(r["health"]) for r in rows if r.get("health", "").replace(".", "").isdigit()]
    if len(healths) > 1:
        first = datetime.fromisoformat(rows[0]["time"])
        last = datetime.fromisoformat(rows[-1]["time"])
        days = max((last - first).days, 1)
        drop = healths[0] - healths[-1]
        lines.append(f"Health:  {healths[0]:.1f}% -> {healths[-1]:.1f}% "
                     f"({drop / days * 30:+.2f} points lost per 30 days)")
    low = sum(p <= 20 for p in percents)
    lines.append(f"Time spent at or below 20%: {low} of {len(rows)} reading(s)")
    return "\n".join(lines)


def describe(report):
    lines = [f"Charge:    {report['percent']}% ({report['status'] or 'unknown'})"
             if report["percent"] is not None else f"Status:    {report['status'] or 'unknown'}"]
    if report["health_percent"] is not None:
        lines.append(f"Health:    {report['health_percent']}% of design capacity "
                     f"({report['health']})")
        lines.append(f"Capacity:  {report['full_capacity']:,} now vs {report['design_capacity']:,}"
                     " when new (mWh or mAh)")
    for label, key, unit in (("Cycles", "cycles", ""), ("Type", "technology", ""),
                             ("Model", "model", ""), ("Draw", "power_watts", " W"),
                             ("Time left", "hours_remaining", " h")):
        if report.get(key) not in (None, ""):
            lines.append(f"{label + ':':<10} {report[key]}{unit}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report battery charge and health.")
    parser.add_argument("--sysfs", type=Path, help="read a power_supply folder (Linux layout)")
    parser.add_argument("--log", type=Path, help="append this reading to a history CSV")
    parser.add_argument("--history", type=Path, help="summarise a history CSV instead")
    parser.add_argument("--min-health", type=float, help="exit 1 if health is below this %%")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)

    if args.history:
        try:
            print(summarise_history(args.history))
        except (OSError, ValueError) as err:
            print(f"Can't read the history: {err}", file=sys.stderr)
            return 1
        return 0
    try:
        report = read_sysfs(args.sysfs) if args.sysfs else read_system()
    except (OSError, ValueError, subprocess.SubprocessError, ET.ParseError) as err:
        print(f"Can't read the battery: {err}", file=sys.stderr)
        return 1
    if report is None:
        print("No battery found (this may be a desktop computer).", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=1) if args.format == "json" else describe(report))
    if args.log:
        fresh = not args.log.exists() or args.log.stat().st_size == 0
        with args.log.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if fresh:
                writer.writerow(HISTORY_FIELDS)
            writer.writerow([datetime.now().isoformat(timespec="seconds"), report["percent"],
                             report["status"], report["health_percent"] or ""])
        print(f"Logged to {args.log}", file=sys.stderr)
    low = (args.min_health is not None and report["health_percent"] is not None
           and report["health_percent"] < args.min_health)
    if low:
        print(f"Health {report['health_percent']}% is below the {args.min_health:g}% minimum.",
              file=sys.stderr)
    return 1 if low else 0


if __name__ == "__main__":
    sys.exit(main())
