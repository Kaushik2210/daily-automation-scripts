"""Stop duplicate or runaway processes by name. Dry-run by default; --apply stops them."""
import argparse
import csv
import fnmatch
import io
import os
import signal
import subprocess  # web-ok: processes are only listed or stopped without --from-file/dry-run
import sys
import time
from pathlib import Path

PROTECTED = {"system", "idle", "registry", "smss", "csrss", "wininit", "winlogon", "services",
             "lsass", "svchost", "dwm", "explorer", "fontdrvhost", "init", "systemd", "launchd",
             "kernel_task", "loginwindow", "windowserver", "finder", "sshd", "dbus-daemon",
             "xorg", "gnome-shell", "kwin", "login", "cron", "python-launcher"}
POWERSHELL = ("Get-Process | ForEach-Object { [pscustomobject]@{Id=$_.Id;"
              "ProcessName=$_.ProcessName;CPU=$_.CPU;WorkingSet64=$_.WorkingSet64;"
              "Age=$(try{((Get-Date)-$_.StartTime).TotalSeconds}catch{''})} } | "
              "ConvertTo-Csv -NoTypeInformation")


def parse_duration(text):
    days = 0
    if "-" in text:
        day_part, text = text.split("-", 1)
        days = int(day_part)
    seconds = 0.0
    for part in text.split(":"):
        seconds = seconds * 60 + float(part)
    return days * 86400 + seconds


def parse_ps(text):
    """Rows of `pid age cputime rss(KB) command`."""
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
            procs.append({"pid": int(row["Id"]), "name": row["ProcessName"],
                          "age": float(row["Age"]) if row.get("Age") else None,
                          "cpu_s": float(row["CPU"] or 0),
                          "mem_mb": int(row["WorkingSet64"] or 0) / 1024 / 1024})
        except (KeyError, ValueError):
            continue
    return procs


def list_processes():
    if os.name == "nt":
        command = ["powershell", "-NoProfile", "-Command", POWERSHELL]
    else:
        command = ["ps", "-axo", "pid=,etime=,cputime=,rss=,comm="]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    if result.returncode:
        raise OSError((result.stderr.strip().splitlines() or ["could not list processes"])[-1])
    return parse_powershell(result.stdout) if os.name == "nt" else parse_ps(result.stdout)


def matches(name, patterns):
    lowered = name.lower().removesuffix(".exe")
    return any(fnmatch.fnmatch(lowered, p.lower().removesuffix(".exe")) for p in patterns)


def plan(procs, patterns, keep, duplicates, cpu_over, mem_over, min_age, mine):
    """Return (to_stop, skipped). Only processes matching `patterns` are ever considered."""
    chosen, skipped = {}, []
    candidates = []
    for proc in procs:
        if not matches(proc["name"], patterns):
            continue
        if proc["pid"] in mine:
            skipped.append({**proc, "why": "this tool or its parent"})
        elif proc["name"].lower().removesuffix(".exe") in PROTECTED or proc["pid"] <= 4:
            skipped.append({**proc, "why": "protected system process"})
        else:
            candidates.append(proc)

    def add(proc, reason):
        if proc["pid"] in chosen:  # several rules can match one process: keep every reason
            chosen[proc["pid"]]["reason"] += f"; {reason}"
        else:
            chosen[proc["pid"]] = {**proc, "reason": reason}

    if duplicates:
        by_name = {}
        for proc in candidates:
            by_name.setdefault(proc["name"], []).append(proc)
        for group in by_name.values():
            group.sort(key=lambda p: (-(p["age"] or 0), p["pid"]))  # oldest first
            for number, proc in enumerate(group[keep:], keep + 1):
                add(proc, f"duplicate: instance {number} of {len(group)} (keeping the oldest "
                          f"{keep})")
    for proc in candidates:
        if proc["age"] is not None and proc["age"] < min_age:
            continue
        average = proc["cpu_s"] / proc["age"] * 100 if proc["age"] else None
        if cpu_over is not None and average is not None and average > cpu_over:
            add(proc, f"runaway: averaging {average:.0f}% CPU since it started")
        if mem_over is not None and proc["mem_mb"] > mem_over:
            add(proc, f"runaway: using {proc['mem_mb']:.0f} MB")
    return sorted(chosen.values(), key=lambda p: (p["name"], p["pid"])), skipped


def is_alive(pid):
    if os.name == "nt":
        result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True,
                                text=True, timeout=30, check=False)
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:  # a finished child that nobody collected yet still answers kill(0)
        return os.waitpid(pid, os.WNOHANG) == (0, 0)
    except ChildProcessError:
        return True


def terminate(pid, force):
    if os.name == "nt":
        command = ["taskkill", "/PID", str(pid)] + (["/F"] if force else [])
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        if result.returncode:
            raise OSError((result.stdout.strip() or result.stderr.strip()).splitlines()[-1])
    else:
        os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)


def stop(pid, grace, force, terminate=terminate, alive=is_alive, sleep=time.sleep):
    """Ask nicely, wait up to `grace` seconds, and only then (with force) kill. Returns outcome.

    Some processes (Windows console programs, for one) refuse a polite request outright; that
    counts as "didn't quit", not as an error, so --force can still deal with them.
    """
    refused = False
    try:
        terminate(pid, False)
    except OSError:
        refused = True
    waited = 0.0
    while not refused and waited < grace:
        if not alive(pid):
            return "stopped"
        sleep(0.25)
        waited += 0.25
    if not alive(pid):
        return "stopped"
    if not force:
        return "still running (use --force to kill it)"
    terminate(pid, True)
    sleep(0.25)
    return "killed" if not alive(pid) else "could not be stopped"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stop duplicate or runaway processes by name.")
    parser.add_argument("names", nargs="+", help="process names or patterns, e.g. node 'python*'")
    parser.add_argument("--duplicates", action="store_true",
                        help="stop extra copies, keeping the oldest --keep of each name")
    parser.add_argument("--keep", type=int, default=1, help="copies to keep with --duplicates (1)")
    parser.add_argument("--cpu-over", type=float,
                        help="stop processes averaging more than this CPU %% since they started")
    parser.add_argument("--mem-over", type=float, help="stop processes using more than this MB")
    parser.add_argument("--min-age", type=float, default=60,
                        help="ignore processes younger than this many seconds (60)")
    parser.add_argument("--grace", type=float, default=5.0,
                        help="seconds to wait after asking a process to quit (5)")
    parser.add_argument("--force", action="store_true", help="kill what ignores the polite request")
    parser.add_argument("--from-file", type=Path, dest="source",
                        help="saved `ps -axo pid=,etime=,cputime=,rss=,comm=` (plan only)")
    parser.add_argument("--apply", action="store_true",
                        help="really stop processes (default only shows the plan)")
    args = parser.parse_args(argv)
    if not (args.duplicates or args.cpu_over is not None or args.mem_over is not None):
        parser.error("choose what to look for: --duplicates, --cpu-over or --mem-over")
    if args.keep < 1 or args.grace < 0 or args.min_age < 0:
        parser.error("--keep must be at least 1; --grace and --min-age can't be negative")
    if args.apply and args.source:
        parser.error("--apply works on the live system, not on --from-file")

    try:
        procs = (parse_ps(args.source.read_text(encoding="utf-8")) if args.source
                 else list_processes())
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as err:
        print(f"Can't read the processes: {err}", file=sys.stderr)
        return 1
    mine = {os.getpid(), os.getppid()}
    targets, skipped = plan(procs, args.names, args.keep, args.duplicates, args.cpu_over,
                            args.mem_over, args.min_age, mine)
    for proc in skipped:
        print(f"skip  {proc['pid']:>7}  {proc['name']}  ({proc['why']})")
    if not targets:
        print("Nothing to stop.")
        return 0
    failures = 0
    for proc in targets:
        label = f"{proc['pid']:>7}  {proc['name']:<18} {proc['mem_mb']:>7.0f} MB  {proc['reason']}"
        if not args.apply:
            print(f"would stop {label}")
            continue
        try:
            outcome = stop(proc["pid"], args.grace, args.force)
        except OSError as err:
            outcome = f"failed: {err}"
        failures += outcome not in ("stopped", "killed")
        print(f"{outcome:<8} {label}")
    if not args.apply:
        print(f"\nDry run: {len(targets)} process(es) would be stopped. Add --apply to do it.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
