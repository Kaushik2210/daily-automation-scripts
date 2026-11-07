"""Ping hosts and log the response times, or analyse saved ping output."""
import argparse
import csv
import re
import subprocess  # web-ok: ping only runs when you give hosts; --parse needs no program
import sys
from datetime import datetime
from pathlib import Path

HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-:]*$")
TIME_RE = re.compile(r"time\s*[=<]\s*([\d.]+)\s*ms", re.IGNORECASE)
LOG_HEADER = ["timestamp", "host", "sent", "received", "loss_percent", "min_ms", "avg_ms", "max_ms"]


def parse_ping(text):
    """Read Linux, macOS or Windows ping output. Returns a dict (values None if unknown)."""
    times = [float(t) for t in TIME_RE.findall(text)]
    info = {"sent": None, "received": None, "loss": None, "min": None, "avg": None, "max": None}
    unix = re.search(r"(\d+) packets transmitted, (\d+) (?:packets )?received", text)
    windows = re.search(r"Sent = (\d+), Received = (\d+)", text)
    found = unix or windows
    if found:
        info["sent"], info["received"] = int(found.group(1)), int(found.group(2))
    elif times:
        info["received"] = len(times)
    rtt = re.search(r"min/avg/max/(?:mdev|stddev)\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)", text)
    win_rtt = re.search(r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms", text)
    if rtt:
        info["min"], info["avg"], info["max"] = (float(rtt.group(i)) for i in (1, 2, 3))
    elif win_rtt:
        info["min"], info["max"], info["avg"] = (float(win_rtt.group(i)) for i in (1, 2, 3))
    elif times:
        info["min"], info["max"], info["avg"] = min(times), max(times), sum(times) / len(times)
    if info["sent"]:
        info["loss"] = round(100 * (info["sent"] - info["received"]) / info["sent"], 1)
    return info


def run_ping(host, count=4):
    """Run the system ping command and return its text output."""
    flag = "-n" if sys.platform.startswith("win") else "-c"
    proc = subprocess.run(["ping", flag, str(count), host], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=count * 5 + 15, check=False)
    return proc.stdout + proc.stderr


def describe(info):
    if not info["received"]:
        return "no replies" if info["sent"] is not None else "couldn't read any results"
    ms = f"min {info['min']:g} / avg {info['avg']:.1f} / max {info['max']:g} ms"
    loss = f", {info['loss']:g}% loss" if info["loss"] is not None else ""
    return f"{info['received']}/{info['sent'] or '?'} replies{loss}, {ms}"


def log_row(path, host, info, now):
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if new:
            writer.writerow(LOG_HEADER)
        writer.writerow([now.strftime("%Y-%m-%d %H:%M:%S"), host, info["sent"], info["received"],
                         info["loss"], info["min"], info["avg"], info["max"]])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ping hosts and log response times.")
    parser.add_argument("hosts", nargs="*", help="host names or IP addresses to ping")
    parser.add_argument("-c", "--count", type=int, default=4, help="pings per host (4)")
    parser.add_argument("--parse", type=Path, help="analyse a saved ping output file instead")
    parser.add_argument("--log", type=Path, help="append each result to this CSV file")
    args = parser.parse_args(argv)
    if not args.hosts and not args.parse:
        parser.error("give hosts to ping, or --parse FILE")
    if not 1 <= args.count <= 100:
        parser.error("--count must be between 1 and 100")

    results = []
    if args.parse:
        if not args.parse.is_file():
            parser.error(f"not a file: {args.parse}")
        text = args.parse.read_text(encoding="utf-8", errors="replace")
        host_match = re.search(r"---\s*(\S+) ping statistics|Pinging (\S+)|PING (\S+)", text)
        host = next((g for g in host_match.groups() if g), args.parse.name) if host_match \
            else args.parse.name
        results.append((host, parse_ping(text)))
    for host in args.hosts:
        if not HOST_RE.match(host):
            print(f"{host}: not a valid host name")
            return 2
        try:
            results.append((host, parse_ping(run_ping(host, args.count))))
        except (OSError, subprocess.TimeoutExpired) as err:
            print(f"{host}: couldn't run ping ({err})")
            return 1
    down = 0
    for host, info in results:
        print(f"{host:<24} {describe(info)}")
        down += not info["received"]
        if args.log:
            log_row(args.log, host, info, datetime.now())
    return 1 if down else 0


if __name__ == "__main__":
    sys.exit(main())
