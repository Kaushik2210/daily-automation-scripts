"""Watch the CPU and memory use of chosen processes, grouped by name."""
import argparse
import csv
import fnmatch
import io
import json
import os
import subprocess  # web-ok: processes are only listed without --from-file
import sys
import time
from pathlib import Path

POWERSHELL = ("Get-Process | Select-Object Id,ProcessName,CPU,WorkingSet64 | "
              "ConvertTo-Csv -NoTypeInformation")


def parse_duration(text):
    """'1-02:03:04', '02:03:04', '03:04' or plain seconds -> seconds (float)."""
    text = text.strip()
    days = 0
    if "-" in text:
        day_part, text = text.split("-", 1)
        days = int(day_part)
    seconds = 0.0
    for part in text.split(":"):
        seconds = seconds * 60 + float(part)
    return days * 86400 + seconds


def parse_ps(text):
    """Rows of `pid age cputime rss(KB) command` -> process dicts. Header lines are skipped."""
    procs = []
    for line in text.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5 or not parts[0].isdigit() or not parts[3].isdigit():
            continue
        try:
            procs.append({"pid": int(parts[0]), "name": os.path.basename(parts[4].strip()),
                          "age": parse_duration(parts[1]), "cpu_s": parse_duration(parts[2]),
                          "mem_mb": int(parts[3]) / 1024})
        except ValueError:
            continue
    return procs


def parse_powershell(text):
    procs = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            procs.append({"pid": int(row["Id"]), "name": row["ProcessName"], "age": None,
                          "cpu_s": float(row["CPU"] or 0),
                          "mem_mb": int(row["WorkingSet64"] or 0) / 1024 / 1024})
        except (KeyError, ValueError):
            continue
    return procs


def list_processes():
    """Running processes on this machine, using the system's own tools."""
    if os.name == "nt":
        command = ["powershell", "-NoProfile", "-Command", POWERSHELL]
    else:
        command = ["ps", "-axo", "pid=,etime=,cputime=,rss=,comm="]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    if result.returncode:
        raise OSError((result.stderr.strip().splitlines() or ["could not list processes"])[-1])
    return parse_powershell(result.stdout) if os.name == "nt" else parse_ps(result.stdout)


def matches(name, patterns):
    return not patterns or any(
        fnmatch.fnmatch(name.lower(), p.lower() if any(c in p for c in "*?[") else f"*{p.lower()}*")
        for p in patterns)


def group(procs, patterns, before=None, interval=None):
    """{name: {count, mem_mb, cpu_s, cpu_pct}}. cpu_pct needs a `before` list and an interval."""
    earlier = {p["pid"]: p["cpu_s"] for p in before or []}
    groups = {}
    for proc in procs:
        if not matches(proc["name"], patterns):
            continue
        item = groups.setdefault(proc["name"], {"count": 0, "mem_mb": 0.0, "cpu_s": 0.0,
                                                "cpu_pct": 0.0 if before else None})
        item["count"] += 1
        item["mem_mb"] += proc["mem_mb"]
        item["cpu_s"] += proc["cpu_s"]
        if before and interval and proc["pid"] in earlier:
            item["cpu_pct"] += max(0.0, proc["cpu_s"] - earlier[proc["pid"]]) / interval * 100
    return groups


def monitor(sampler, patterns, interval, count, sleep=time.sleep):
    """Yield one {name: stats} dict per sample. 100% of CPU means one full core."""
    previous = sampler()
    for _ in range(count):
        sleep(interval)
        current = sampler()
        yield group(current, patterns, previous, interval)
        previous = current


def alerts(groups, cpu_over, mem_over):
    found = []
    for name, g in groups.items():
        if cpu_over is not None and g["cpu_pct"] is not None and g["cpu_pct"] > cpu_over:
            found.append(f"{name}: CPU {g['cpu_pct']:.0f}% is over {cpu_over:g}%")
        if mem_over is not None and g["mem_mb"] > mem_over:
            found.append(f"{name}: memory {g['mem_mb']:.0f} MB is over {mem_over:g} MB")
    return found


def hms(seconds):
    return f"{int(seconds // 3600)}:{int(seconds % 3600 // 60):02d}:{int(seconds % 60):02d}"


def render(groups, top, live):
    if live:  # busiest CPU first, memory breaks ties
        ordered = sorted(groups.items(), key=lambda kv: (-kv[1]["cpu_pct"], -kv[1]["mem_mb"]))
    else:  # a single snapshot has no CPU %, so rank by memory
        ordered = sorted(groups.items(), key=lambda kv: -kv[1]["mem_mb"])
    ordered = ordered[:top] if top else ordered
    width = max([len(n) for n, _ in ordered] + [7])
    head = f"{'process':<{width}}  {'count':>5}  {'memory MB':>10}  " + (
        f"{'CPU %':>7}" if live else f"{'CPU time':>9}")
    lines = [head]
    for name, g in ordered:
        last = f"{g['cpu_pct']:>7.1f}" if live else f"{hms(g['cpu_s']):>9}"
        lines.append(f"{name:<{width}}  {g['count']:>5}  {g['mem_mb']:>10.1f}  {last}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Watch CPU and memory of chosen processes.")
    parser.add_argument("names", nargs="*", help="process names or patterns (all if none)")
    parser.add_argument("--from-file", type=Path, dest="source",
                        help="saved `ps -axo pid=,etime=,cputime=,rss=,comm=` output")
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between samples (2)")
    parser.add_argument("--count", type=int, default=1, help="samples to take (1)")
    parser.add_argument("--top", type=int, default=15, help="show this many processes (15)")
    parser.add_argument("--cpu-over", type=float, help="alert above this CPU %% (100 = one core)")
    parser.add_argument("--mem-over", type=float, help="alert above this memory in MB")
    parser.add_argument("--format", choices=["text", "json", "csv"], default="text")
    args = parser.parse_args(argv)
    if args.interval <= 0 or args.count < 1 or args.top < 0:
        parser.error("--interval must be above 0, --count at least 1 and --top not negative")

    try:
        if args.source:
            samples = [group(parse_ps(args.source.read_text(encoding="utf-8")), args.names)]
        else:
            samples = list(monitor(list_processes, args.names, args.interval, args.count))
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as err:
        print(f"Can't read the processes: {err}", file=sys.stderr)
        return 1
    live = not args.source
    if not samples[-1]:
        print("No matching processes.", file=sys.stderr)
        return 1

    problems = []
    for number, groups in enumerate(samples, 1):
        if args.format == "text":
            print(render(groups, args.top, live) + ("\n" if number < len(samples) else ""))
        problems += alerts(groups, args.cpu_over, args.mem_over)
    if args.format == "json":
        print(json.dumps(samples[-1], indent=1))
    elif args.format == "csv":
        print("process,count,memory_mb,cpu_percent,cpu_seconds")
        for name, g in samples[-1].items():
            pct = "" if g["cpu_pct"] is None else f"{g['cpu_pct']:.1f}"
            print(f'"{name}",{g["count"]},{g["mem_mb"]:.1f},{pct},{g["cpu_s"]:.1f}')
    for problem in dict.fromkeys(problems):
        print(f"ALERT {problem}", file=sys.stderr if args.format != "text" else sys.stdout)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
