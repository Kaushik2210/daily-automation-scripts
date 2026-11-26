"""Log CPU, memory and disk use to a CSV file at a fixed interval."""
import argparse
import csv
import json
import os
import platform
import random
import re
import shutil
import subprocess  # web-ok: only used on Windows and macOS for numbers the stdlib can't read
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

FIELDS = ["time", "cpu_percent", "memory_percent", "memory_used_mb", "disk_percent",
          "disk_free_gb"]


def parse_proc_stat(text):
    """First line of /proc/stat -> (idle ticks, total ticks)."""
    numbers = [int(x) for x in text.splitlines()[0].split()[1:]]
    return numbers[3] + (numbers[4] if len(numbers) > 4 else 0), sum(numbers[:8])


def parse_meminfo(text):
    """/proc/meminfo -> (used MB, total MB), where used = total - available."""
    pattern = re.compile(r"^(\w+):\s+(\d+)", re.MULTILINE)
    values = {m.group(1): int(m.group(2)) for m in pattern.finditer(text)}
    total = values["MemTotal"]
    return (total - values.get("MemAvailable", values.get("MemFree", 0))) / 1024, total / 1024


def parse_top_mac(text):
    """`top -l 1` CPU line -> busy percent."""
    match = re.search(r"([\d.]+)%\s+idle", text)
    return round(100 - float(match.group(1)), 1) if match else None


def parse_vm_stat(text, total_bytes):
    """`vm_stat` + total memory -> (used MB, total MB); used = active + wired + compressed."""
    size = int(re.search(r"page size of (\d+) bytes", text).group(1))
    pages = {k: int(v) for k, v in re.findall(r"Pages ([\w ]+?):\s+(\d+)\.", text)}
    used = sum(pages.get(k, 0) for k in ("active", "wired down", "occupied by compressor"))
    return used * size / 1024 / 1024, total_bytes / 1024 / 1024


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode:
        raise OSError(result.stderr.strip() or f"{command[0]} failed")
    return result.stdout


class Sampler:
    """Reads the machine's CPU, memory and disk. CPU % needs the previous reading."""

    def __init__(self, disk_path):
        self.disk_path = disk_path
        self.system = platform.system()
        self.last_ticks = None

    def cpu(self):
        if self.system == "Linux":
            idle, total = parse_proc_stat(Path("/proc/stat").read_text())
            previous, self.last_ticks = self.last_ticks, (idle, total)
            if previous is None:
                time.sleep(0.25)
                return self.cpu()
            span = total - previous[1]
            return round(100 * (1 - (idle - previous[0]) / span), 1) if span else 0.0
        if self.system == "Darwin":
            return parse_top_mac(run(["top", "-l", "1", "-n", "0"]))
        script = ("(Get-CimInstance Win32_Processor | Measure-Object LoadPercentage "
                  "-Average).Average")
        return float(run(["powershell", "-NoProfile", "-Command", script]).strip())

    def memory(self):
        """(used MB, total MB)"""
        if self.system == "Linux":
            return parse_meminfo(Path("/proc/meminfo").read_text())
        if self.system == "Darwin":
            total = int(run(["sysctl", "-n", "hw.memsize"]))
            return parse_vm_stat(run(["vm_stat"]), total)
        script = ("$o = Get-CimInstance Win32_OperatingSystem; "
                  "ConvertTo-Json @($o.TotalVisibleMemorySize, $o.FreePhysicalMemory)")
        total, free = json.loads(run(["powershell", "-NoProfile", "-Command", script]))
        return (total - free) / 1024, total / 1024

    def sample(self, now=None):
        disk = shutil.disk_usage(self.disk_path)
        used, total = self.memory()
        return {"time": (now or datetime.now()).isoformat(timespec="seconds"),
                "cpu_percent": self.cpu(), "memory_percent": round(used / total * 100, 1),
                "memory_used_mb": round(used),
                "disk_percent": round(disk.used / disk.total * 100, 1),
                "disk_free_gb": round(disk.free / 1024**3, 1)}


class Simulator:
    """Repeatable made-up readings for demos and tests (no real machine needed)."""

    def __init__(self, start, interval, seed=7):
        self.rng, self.now, self.step, self.n = random.Random(seed), start, interval, 0

    def sample(self, now=None):
        stamp, self.now, self.n = self.now, self.now + timedelta(seconds=self.step), self.n + 1
        return {"time": stamp.isoformat(timespec="seconds"),
                "cpu_percent": round(self.rng.uniform(5, 60) + (30 if self.n % 4 == 0 else 0), 1),
                "memory_percent": round(55 + self.n * 0.7 + self.rng.uniform(-1, 1), 1),
                "memory_used_mb": round(8800 + self.n * 110 + self.rng.uniform(-40, 40)),
                "disk_percent": round(71.2 + self.n * 0.05, 1), "disk_free_gb": 142.3}


def summary(rows):
    lines = []
    for field in ("cpu_percent", "memory_percent", "disk_percent"):
        values = [r[field] for r in rows if r[field] is not None]
        if values:
            lines.append(f"{field.replace('_percent', ''):<7} min {min(values):>5.1f}  "
                         f"avg {sum(values) / len(values):>5.1f}  max {max(values):>5.1f}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Log CPU, memory and disk use to CSV.")
    parser.add_argument("--output", type=Path, help="CSV file to write (a new file)")
    parser.add_argument("--append", action="store_true", help="add to --output if it exists")
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between samples (5)")
    parser.add_argument("--count", type=int, default=12, help="number of samples (12)")
    parser.add_argument("--disk", default=os.path.abspath(os.sep), help="path whose disk to watch")
    parser.add_argument("--simulate", action="store_true",
                        help="repeatable fake readings instead of the real machine (for demos)")
    parser.add_argument("--start", help="first timestamp for --simulate, e.g. 2026-11-26T09:00:00")
    parser.add_argument("--quiet", action="store_true", help="don't print each sample")
    args = parser.parse_args(argv)
    if args.interval < 0 or args.count < 1:
        parser.error("--interval can't be negative and --count must be at least 1")
    try:
        start = datetime.fromisoformat(args.start) if args.start else datetime(2026, 1, 1, 9, 0)
    except ValueError:
        parser.error(f"--start must look like 2026-11-26T09:00:00, got '{args.start}'")
    if args.output and args.output.exists() and not args.append:
        print(f"{args.output} already exists; use --append to add to it.", file=sys.stderr)
        return 1

    reader = Simulator(start, args.interval) if args.simulate else Sampler(args.disk)
    rows, writer, handle = [], None, None
    try:
        if args.output:
            fresh = not args.output.exists() or args.output.stat().st_size == 0
            handle = args.output.open("a", newline="", encoding="utf-8")
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            if fresh:
                writer.writeheader()
        for number in range(args.count):
            if number and not args.simulate:
                time.sleep(args.interval)
            row = reader.sample()
            rows.append(row)
            if writer:
                writer.writerow(row)
                handle.flush()
            if not args.quiet:
                print(f"{row['time']}  cpu {row['cpu_percent']:>5}%  "
                      f"mem {row['memory_percent']:>5}% ({row['memory_used_mb']} MB)  "
                      f"disk {row['disk_percent']:>5}% ({row['disk_free_gb']} GB free)")
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as err:
        print(f"Can't read the machine's numbers: {err}", file=sys.stderr)
        return 1
    finally:
        if handle:
            handle.close()
    if rows:
        print("\n" + summary(rows))
        if args.output:
            print(f"Logged {len(rows)} sample(s) to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
