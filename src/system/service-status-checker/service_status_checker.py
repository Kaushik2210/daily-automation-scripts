"""Check whether named services are running (systemd, Windows services or launchd)."""
import argparse
import json
import platform
import re
import subprocess  # web-ok: the system is only queried without --from-file
import sys
from pathlib import Path

STATES = {"RUNNING": "running", "STOPPED": "stopped"}


def parse_systemctl(text):
    """`systemctl list-units --type=service --all --no-legend --plain` -> service dicts."""
    services = []
    for line in text.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 4 or not parts[0].endswith(".service"):
            continue
        unit, _load, active, sub = parts[:4]
        state = ("failed" if active == "failed" else "stopped" if active in ("inactive", "dead")
                 else "running" if active == "active" else active)
        services.append({"name": unit.removesuffix(".service"), "display": parts[4].strip()
                         if len(parts) > 4 else "", "state": state, "detail": f"{active}/{sub}"})
    return services


def parse_sc(text):
    """`sc query state= all` blocks -> service dicts."""
    services = []
    for block in re.split(r"\n\s*\n", text.replace("\r", "")):
        name = re.search(r"SERVICE_NAME:\s*(.+)", block)
        state = re.search(r"STATE\s*:\s*\d+\s+(\w+)", block)
        if name and state:
            display = re.search(r"DISPLAY_NAME:\s*(.+)", block)
            word = state.group(1)
            services.append({"name": name.group(1).strip(),
                             "display": display.group(1).strip() if display else "",
                             "state": STATES.get(word, word.lower().replace("_", " ")),
                             "detail": word})
    return services


def parse_launchctl(text):
    """`launchctl list` rows of `PID  Status  Label` -> service dicts."""
    services = []
    for line in text.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or not (parts[0].isdigit() or parts[0] == "-"):
            continue
        if parts[1].lstrip("-").isdigit():
            state = ("running" if parts[0].isdigit()
                     else "stopped" if parts[1] == "0" else "failed")
            services.append({"name": parts[2].strip(), "display": "", "state": state,
                             "detail": f"pid {parts[0]}, exit {parts[1]}"})
    return services


def detect_and_parse(text):
    if "SERVICE_NAME:" in text:
        return parse_sc(text)
    if ".service" in text:
        return parse_systemctl(text)
    return parse_launchctl(text)


def collect(system, run=subprocess.run):
    commands = {"Windows": ["sc", "query", "state=", "all"], "Darwin": ["launchctl", "list"]}
    command = commands.get(system, ["systemctl", "list-units", "--type=service", "--all",
                                    "--no-legend", "--plain", "--no-pager"])
    result = run(command, capture_output=True, text=True, timeout=60, check=False)
    if result.returncode:
        raise OSError((result.stderr.strip().splitlines() or [f"{command[0]} failed"])[-1])
    return detect_and_parse(result.stdout)


def find(services, wanted):
    """Best match: exact name (with or without .service), then display name, then substring."""
    key = wanted.lower().removesuffix(".service")
    for test in (lambda s: s["name"].lower() == key, lambda s: s["display"].lower() == key,
                 lambda s: key in s["name"].lower() or key in s["display"].lower()):
        found = [s for s in services if test(s)]
        if found:
            return found[0]
    return None


def check(services, names, expect):
    """One result per requested name; ok is True when the state is what was expected."""
    results = []
    for name in names:
        service = find(services, name)
        if service is None:
            results.append({"requested": name, "name": None, "state": "not found", "ok": False})
        else:
            results.append({"requested": name, "name": service["name"], "state": service["state"],
                            "detail": service["detail"], "ok": service["state"] == expect})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check whether services are running.")
    parser.add_argument("names", nargs="*", help="service names (or part of the display name)")
    parser.add_argument("--from-file", type=Path, dest="source",
                        help="saved `systemctl list-units`, `sc query` or `launchctl list` output")
    parser.add_argument("--expect", choices=["running", "stopped"], default="running",
                        help="the state that counts as OK (running)")
    parser.add_argument("--list", action="store_true", help="list every service found")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    if not args.names and not args.list:
        parser.error("give service names, or use --list")
    try:
        services = (detect_and_parse(args.source.read_text(encoding="utf-8")) if args.source
                    else collect(platform.system()))
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as err:
        print(f"Can't read the services: {err}", file=sys.stderr)
        return 1
    if not services:
        print("No services were found in that output.", file=sys.stderr)
        return 1

    results = check(services, args.names, args.expect)
    if args.format == "json":
        print(json.dumps({"results": results, "services": services if args.list else None},
                         indent=1))
    else:
        for r in results:
            mark = "OK  " if r["ok"] else "FAIL"
            label = r["name"] or r["requested"]
            extra = f" ({r['detail']})" if r.get("detail") else ""
            print(f"{mark} {label}: {r['state']}{extra}")
        if args.list:
            width = max(len(s["name"]) for s in services)
            for s in sorted(services, key=lambda s: (s["state"], s["name"])):
                print(f"  {s['name']:<{width}}  {s['state']:<9} {s['display']}".rstrip())
        if results:
            bad = sum(not r["ok"] for r in results)
            print(f"\n{len(results) - bad} of {len(results)} as expected ({args.expect}).")
    return 1 if any(not r["ok"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
