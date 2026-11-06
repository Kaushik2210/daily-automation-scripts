"""Show the entries of the hosts file as a readable table."""
import argparse
import os
import sys
from pathlib import Path


def default_hosts_path():
    root = os.environ.get("SYSTEMROOT", r"C:\Windows")
    if os.name == "nt":
        return Path(root) / "System32" / "drivers" / "etc" / "hosts"
    return Path("/etc/hosts")


def parse_hosts(text):
    """Return a list of dicts with ip, names, comment and active (False if commented out)."""
    entries = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        active = not line.startswith("#")
        body, _, comment = line.lstrip("# ").partition("#")
        parts = body.split()
        if len(parts) < 2 or ("." not in parts[0] and ":" not in parts[0]):
            continue  # an ordinary comment, not a host entry
        entries.append({"line": number, "ip": parts[0], "names": parts[1:],
                        "comment": comment.strip(), "active": active})
    return entries


def find_duplicates(entries):
    """Names pointing to different addresses of the same kind (IPv4 or IPv6)."""
    seen, dupes = {}, set()
    for entry in entries:
        if not entry["active"]:
            continue
        family = ":" in entry["ip"]
        for name in entry["names"]:
            key = (name.lower(), family)
            if key in seen and seen[key] != entry["ip"]:
                dupes.add(name)
            seen[key] = entry["ip"]
    return sorted(dupes)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Show the hosts file as a table.")
    parser.add_argument("--file", type=Path, default=None, help="hosts file (default: system one)")
    parser.add_argument("--search", default="", help="only show entries containing this text")
    parser.add_argument("--all", action="store_true", help="include commented-out entries")
    args = parser.parse_args(argv)

    path = args.file or default_hosts_path()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as err:
        print(f"Can't read {path}: {err}", file=sys.stderr)
        return 1
    entries = [e for e in parse_hosts(text) if args.all or e["active"]]
    needle = args.search.lower()
    entries = [e for e in entries if needle in f"{e['ip']} {' '.join(e['names'])}".lower()]

    print(f"{'line':>4}  {'address':<18}{'names':<40}note")
    for e in entries:
        flag = "" if e["active"] else "(off) "
        print(f"{e['line']:>4}  {e['ip']:<18}{', '.join(e['names']):<40}{flag}{e['comment']}")
    dupes = find_duplicates(entries)
    print(f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'} from {path}.")
    if dupes:
        print(f"Warning: names pointing to different addresses: {', '.join(dupes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
