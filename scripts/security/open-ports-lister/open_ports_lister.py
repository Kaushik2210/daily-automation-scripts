"""List the TCP ports this computer is listening on, and which program owns each one."""
import argparse
import csv
import io
import re
import subprocess  # web-ok: the system tools only run when you don't pass --parse FILE
import sys
from pathlib import Path

NAMES = {21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns", 80: "http", 110: "pop3",
         135: "msrpc", 139: "netbios", 143: "imap", 443: "https", 445: "smb", 631: "cups",
         993: "imaps", 1433: "mssql", 3000: "dev server", 3306: "mysql", 3389: "rdp",
         5000: "dev server", 5432: "postgresql", 5900: "vnc", 6379: "redis", 8000: "dev server",
         8080: "http-alt", 8443: "https-alt", 9200: "elasticsearch", 27017: "mongodb"}
RISKY = {21, 23, 135, 139, 445, 1433, 3306, 3389, 5432, 5900, 6379, 9200, 11211, 27017}
WILDCARDS = {"0.0.0.0", "::", "*", "[::]"}


def split_address(text):
    """'0.0.0.0:80' / '[::1]:5432' / '*:80' / '127.0.0.1:631' -> (address, port or None)."""
    host, _, port = text.rpartition(":")
    host = host.strip("[]") or "*"
    return host, int(port) if port.isdigit() else None


def parse_ss(text):
    entries = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0] not in ("LISTEN", "UNCONN"):
            continue
        host, port = split_address(parts[3])
        process = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
        if port:
            entries.append({"proto": "tcp" if parts[0] == "LISTEN" else "udp", "address": host,
                            "port": port, "process": process.group(1) if process else "",
                            "pid": int(process.group(2)) if process else None})
    return entries


def parse_windows_netstat(text):
    entries = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0] == "TCP" and parts[3] == "LISTENING":
            host, port = split_address(parts[1])
            entries.append({"proto": "tcp", "address": host, "port": port, "process": "",
                            "pid": int(parts[4])})
        elif len(parts) >= 4 and parts[0] == "UDP" and parts[1] != "*:*":
            host, port = split_address(parts[1])
            entries.append({"proto": "udp", "address": host, "port": port, "process": "",
                            "pid": int(parts[-1]) if parts[-1].isdigit() else None})
    return entries


def parse_lsof(text):
    entries = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 9 and "(LISTEN)" in line and parts[7] == "TCP":
            host, port = split_address(parts[8])
            entries.append({"proto": "tcp", "address": host, "port": port,
                            "process": parts[0], "pid": int(parts[1])})
    return entries


def parse_listing(text):
    """Work out which tool produced `text` and parse it."""
    if "Local Address" in text and "Foreign Address" in text:
        return parse_windows_netstat(text)
    if "COMMAND" in text and "(LISTEN)" in text:
        return parse_lsof(text)
    return parse_ss(text)


def merge(entries):
    """One row per (protocol, port, program): addresses are combined (IPv4 + IPv6)."""
    rows = {}
    for entry in entries:
        key = (entry["proto"], entry["port"], entry["pid"], entry["process"])
        row = rows.setdefault(key, {**entry, "addresses": set()})
        row["addresses"].add(entry["address"])
    for row in rows.values():
        row["exposed"] = bool(row["addresses"] & WILDCARDS) or any(
            not a.startswith(("127.", "::1")) and a not in WILDCARDS for a in row["addresses"])
    return sorted(rows.values(), key=lambda r: (r["port"], r["proto"]))


def run(command):
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=30, check=False).stdout


def collect():
    """Ask this computer's own tools for its listening ports (read-only commands)."""
    if sys.platform.startswith("win"):
        entries = parse_windows_netstat(run(["netstat", "-ano"]))
        names = {}
        for row in csv.reader(io.StringIO(run(["tasklist", "/FO", "CSV", "/NH"]))):
            if len(row) >= 2 and row[1].isdigit():
                names[int(row[1])] = row[0]
        for entry in entries:
            entry["process"] = names.get(entry["pid"], "")
        return entries
    if sys.platform == "darwin":
        return parse_lsof(run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"]))
    return parse_ss(run(["ss", "-H", "-ltnup"]) or run(["ss", "-ltnup"]))


def main(argv=None):
    parser = argparse.ArgumentParser(description="List listening ports on this computer.")
    parser.add_argument("--parse", type=Path,
                        help="read saved output of netstat -ano, ss -ltnp or lsof instead")
    parser.add_argument("--only-exposed", action="store_true",
                        help="hide ports reachable only from this computer")
    args = parser.parse_args(argv)
    try:
        entries = (parse_listing(args.parse.read_text(encoding="utf-8", errors="replace"))
                   if args.parse else collect())
    except (OSError, subprocess.SubprocessError) as err:
        print(f"Couldn't list the ports: {err}", file=sys.stderr)
        return 1
    rows = merge(entries)
    if args.only_exposed:
        rows = [r for r in rows if r["exposed"]]
    if not rows:
        print("No listening ports found." if not args.parse else
              "No listening ports found in that file.")
        return 1
    print(f"{'Port':>5}  {'Proto':<5}  {'Reachable from':<16}  {'Service':<12}  Program")
    risky = 0
    for row in rows:
        where = "all interfaces" if row["addresses"] & WILDCARDS else (
            "this computer" if not row["exposed"] else ", ".join(sorted(row["addresses"]))[:16])
        program = f"{row['process']} (pid {row['pid']})" if row["pid"] else (row["process"] or "-")
        flag = ""
        if row["exposed"] and row["port"] in RISKY:
            flag = "   <-- risky to expose"
            risky += 1
        print(f"{row['port']:>5}  {row['proto']:<5}  {where:<16}  "
              f"{NAMES.get(row['port'], '-'):<12}  {program}{flag}")
    exposed = sum(r["exposed"] for r in rows)
    print(f"\n{len(rows)} listening port(s): {exposed} reachable from other computers, "
          f"{len(rows) - exposed} local only.")
    if risky:
        print(f"{risky} exposed service(s) are usually better kept local or behind a firewall.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
