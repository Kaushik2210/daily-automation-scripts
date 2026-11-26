"""Export recent system events (journald, Windows Event Log or macOS log) to a file."""
import argparse
import csv
import io
import json
import platform
import re
import subprocess  # web-ok: the system log is only read without --from-file
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

LEVELS = ["info", "warning", "error"]  # lowest to highest
FIELDS = ["time", "level", "source", "id", "message"]


def iso(moment):
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def event(moment, level, source, event_id, message):
    return {"time": iso(moment), "level": level, "source": source or "", "id": event_id,
            "message": " ".join(str(message or "").split())}


def parse_journal(text):
    """`journalctl -o json` lines (priority 0-3 error, 4 warning, otherwise info)."""
    events = []
    for line in text.splitlines():
        try:
            row = json.loads(line)
            moment = datetime.fromtimestamp(int(row["__REALTIME_TIMESTAMP"]) / 1e6, UTC)
        except (ValueError, KeyError, TypeError):
            continue
        priority = int(row.get("PRIORITY", 6))
        message = row.get("MESSAGE", "")
        if isinstance(message, list):  # journald encodes binary messages as byte lists
            message = bytes(message).decode("utf-8", "replace")
        events.append(event(moment, "error" if priority <= 3 else "warning" if priority == 4
                            else "info", row.get("_SYSTEMD_UNIT") or row.get("SYSLOG_IDENTIFIER"),
                            None, message))
    return events


def powershell_time(value):
    """Windows PowerShell 5 writes /Date(ms)/; newer versions write ISO text."""
    match = re.search(r"/Date\((-?\d+)", str(value))
    if match:
        return datetime.fromtimestamp(int(match.group(1)) / 1000, UTC)
    return datetime.fromisoformat(str(value))


def parse_windows(text):
    """`Get-WinEvent ... | ConvertTo-Json` output (one object or a list)."""
    data = json.loads(text) if text.strip() else []
    events = []
    for row in data if isinstance(data, list) else [data]:
        try:
            level = {"critical": "error", "error": "error", "warning": "warning"}.get(
                str(row.get("LevelDisplayName", "")).lower(), "info")
            events.append(event(powershell_time(row["TimeCreated"]), level, row.get("ProviderName"),
                                row.get("Id"), row.get("Message")))
        except (KeyError, ValueError, AttributeError):
            continue
    return events


def parse_mac(text):
    """`log show --style ndjson` lines."""
    events = []
    for line in text.splitlines():
        try:
            row = json.loads(line)
            moment = datetime.fromisoformat(row["timestamp"])
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=UTC)
        except (ValueError, KeyError, TypeError):
            continue
        kind = str(row.get("messageType", "")).lower()
        events.append(event(moment, "error" if kind in ("error", "fault") else "info",
                            Path(row.get("processImagePath", "")).name, None,
                            row.get("eventMessage")))
    return events


def parse_any(text):
    stripped = text.lstrip()
    if stripped.startswith(("[", "{\n", '{"TimeCreated')) or '"TimeCreated"' in stripped[:400]:
        return parse_windows(text)
    if "__REALTIME_TIMESTAMP" in text[:2000]:
        return parse_journal(text)
    return parse_mac(text)


def read_system(hours, limit, minimum, run=subprocess.run, system=None):
    system = system or platform.system()
    if system == "Windows":
        levels = {"error": "1,2", "warning": "1,2,3", "info": "1,2,3,4"}[minimum]
        script = (f"$s=(Get-Date).AddHours(-{hours}); Get-WinEvent -FilterHashtable "
                  f"@{{LogName='System','Application';StartTime=$s;Level={levels}}} "
                  f"-MaxEvents {limit} -ErrorAction SilentlyContinue | Select-Object "
                  "TimeCreated,LevelDisplayName,ProviderName,Id,Message | ConvertTo-Json")
        command = ["powershell", "-NoProfile", "-Command", script]
    elif system == "Darwin":
        predicate = {"error": "messageType == error OR messageType == fault",
                     "warning": "messageType == error OR messageType == fault",
                     "info": "messageType != debug"}[minimum]
        command = ["log", "show", "--last", f"{hours}h", "--style", "ndjson", "--predicate",
                   predicate]
    else:
        priority = {"error": "err", "warning": "warning", "info": "info"}[minimum]
        command = ["journalctl", "--since", f"{hours} hours ago", "-p", priority, "-o", "json",
                   "--no-pager", "-n", str(limit)]
    try:
        result = run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                     timeout=300, check=False)
    except FileNotFoundError:
        raise OSError(f"'{command[0]}' is not installed on this system") from None
    if result.returncode and not result.stdout.strip():
        raise OSError((result.stderr.strip().splitlines() or [f"{command[0]} failed"])[-1])
    return result.stdout


def select(events, minimum, hours, contains, source):
    floor = LEVELS.index(minimum)
    chosen = [e for e in events if LEVELS.index(e["level"]) >= floor]
    if hours and chosen:
        cutoff = max(datetime.fromisoformat(e["time"]) for e in events)
        cutoff -= timedelta(hours=hours)
        chosen = [e for e in chosen if datetime.fromisoformat(e["time"]) >= cutoff]
    if contains:
        chosen = [e for e in chosen if contains.lower() in e["message"].lower()]
    if source:
        chosen = [e for e in chosen if source.lower() in e["source"].lower()]
    return sorted(chosen, key=lambda e: e["time"])


def render(events, fmt):
    if fmt == "json":
        return json.dumps(events, indent=1)
    if fmt == "jsonl":
        return "\n".join(json.dumps(e) for e in events)
    if fmt == "text":
        return "\n".join(f"{e['time']}  {e['level'].upper():<7} {e['source']}: {e['message']}"
                         for e in events)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(events)
    return buffer.getvalue().rstrip("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export recent system events to a file.")
    parser.add_argument("--output", type=Path, help="write to this new file (else print)")
    parser.add_argument("--force", action="store_true", help="overwrite --output if it exists")
    parser.add_argument("--format", choices=["csv", "json", "jsonl", "text"], default="csv")
    parser.add_argument("--level", choices=LEVELS, default="warning",
                        help="lowest level to include (warning)")
    parser.add_argument("--hours", type=float, help="only the last N hours (24 when reading live)")
    parser.add_argument("--limit", type=int, default=1000, help="at most this many events (1000)")
    parser.add_argument("--contains", help="only messages containing this text")
    parser.add_argument("--source", help="only events whose source contains this text")
    parser.add_argument("--from-file", type=Path, dest="saved",
                        help="saved journalctl -o json, Get-WinEvent JSON or `log show` ndjson")
    args = parser.parse_args(argv)
    if args.limit < 1 or (args.hours is not None and args.hours <= 0):
        parser.error("--limit must be at least 1 and --hours above 0")
    if args.output and args.output.exists() and not args.force:
        print(f"{args.output} already exists; use --force to overwrite it.", file=sys.stderr)
        return 1
    try:
        text = (args.saved.read_text(encoding="utf-8") if args.saved
                else read_system(args.hours or 24, args.limit, args.level))
        events = parse_any(text)
    except (OSError, ValueError, UnicodeDecodeError, subprocess.SubprocessError) as err:
        print(f"Can't read the events: {err}", file=sys.stderr)
        return 1
    chosen = select(events, args.level, args.hours if args.saved else None, args.contains,
                    args.source)[-args.limit:]
    if not chosen:
        print(f"No {args.level}-or-higher events matched ({len(events)} read).", file=sys.stderr)
        return 1
    body = render(chosen, args.format)
    counts = Counter(e["level"] for e in chosen)
    top = Counter(e["source"] for e in chosen).most_common(3)
    summary = (f"{len(chosen)} event(s): " + ", ".join(f"{counts[lv]} {lv}" for lv in
                                                        reversed(LEVELS) if counts[lv])
               + "; top sources: " + ", ".join(f"{name or '?'} ({n})" for name, n in top))
    if args.output:
        args.output.write_text(body + "\n", encoding="utf-8")
        print(f"Wrote {args.output}\n{summary}")
    else:
        print(body)
        print(f"\n{summary}", file=sys.stderr if args.format in ("json", "jsonl", "csv") else
              sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
