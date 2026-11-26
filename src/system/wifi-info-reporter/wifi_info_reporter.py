"""Report the current Wi-Fi network, signal strength and speed (Windows, macOS and Linux)."""
import argparse
import json
import os
import platform
import re
import subprocess  # web-ok: the system is only queried without --from-file
import sys
from pathlib import Path

AIRPORT = ("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/"
           "Resources/airport")


def rssi_to_percent(rssi):
    """Rough quality from signal strength: -100 dBm is 0%, -50 dBm or better is 100%."""
    return max(0, min(100, 2 * (int(rssi) + 100)))


def percent_to_rssi(percent):
    return round(int(percent) / 2 - 100)


def quality(percent):
    return ("excellent" if percent >= 75 else "good" if percent >= 50
            else "fair" if percent >= 30 else "weak")


def band(channel=None, mhz=None):
    if mhz:
        return "2.4 GHz" if mhz < 3000 else "5 GHz" if mhz < 5925 else "6 GHz"
    if channel:
        return "2.4 GHz" if channel <= 14 else "5 GHz"
    return None


def first_int(text):
    match = re.search(r"\d+", text or "")
    return int(match.group()) if match else None


def parse_netsh(text):
    fields = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and key.strip() not in fields:
            fields[key.strip().lower()] = value.strip()
    if not fields.get("ssid") or fields.get("state", "").lower() != "connected":
        return None
    percent = first_int(fields.get("signal"))
    channel = first_int(fields.get("channel"))
    return {"ssid": fields["ssid"], "signal_percent": percent,
            "rssi_dbm": percent_to_rssi(percent) if percent is not None else None,
            "channel": channel, "band": band(channel), "security": fields.get("authentication"),
            "rate_mbps": float(fields["receive rate (mbps)"])
            if fields.get("receive rate (mbps)", "").replace(".", "").isdigit() else None,
            "bssid": fields.get("bssid"), "radio": fields.get("radio type")}


def parse_airport(text):
    fields = dict(re.findall(r"^\s*([\w .]+?):\s*(.*)$", text, re.MULTILINE))
    if not fields.get("SSID"):
        return None
    rssi = int(fields["agrCtlRSSI"]) if fields.get("agrCtlRSSI", "").lstrip("-").isdigit() else None
    channel = first_int(fields.get("channel"))
    noise = fields.get("agrCtlNoise", "")
    return {"ssid": fields["SSID"], "signal_percent": rssi_to_percent(rssi) if rssi else None,
            "rssi_dbm": rssi, "channel": channel, "band": band(channel),
            "security": fields.get("link auth"), "rate_mbps": first_int(fields.get("lastTxRate")),
            "bssid": fields.get("BSSID"), "noise_dbm": int(noise) if noise.lstrip("-").isdigit()
            else None}


def split_terse(line):
    """nmcli -t escapes ':' inside values as '\\:'."""
    return [part.replace("\\:", ":") for part in re.split(r"(?<!\\):", line)]


def parse_nmcli(text):
    """`nmcli -t -f ACTIVE,SSID,SIGNAL,CHAN,FREQ,SECURITY dev wifi` -> every network seen."""
    networks = []
    for line in text.splitlines():
        parts = split_terse(line.strip())
        if len(parts) < 6 or not parts[1]:
            continue
        percent, channel = first_int(parts[2]), first_int(parts[3])
        networks.append({"ssid": parts[1], "active": parts[0] == "yes", "signal_percent": percent,
                         "rssi_dbm": percent_to_rssi(percent) if percent is not None else None,
                         "channel": channel, "band": band(channel, first_int(parts[4])),
                         "security": parts[5] or "open", "rate_mbps": None, "bssid": None})
    return networks


def parse_any(text):
    """Return (current connection or None, other networks) for any supported output."""
    if "agrCtlRSSI" in text:
        return parse_airport(text), []
    if "BSSID" in text and "State" in text:
        return parse_netsh(text), []
    networks = parse_nmcli(text)
    current = next((n for n in networks if n["active"]), None)
    return current, [n for n in networks if n is not current]


def read_system(run=subprocess.run, system=None):
    system = system or platform.system()
    if system == "Windows":
        command = ["netsh", "wlan", "show", "interfaces"]
    elif system == "Darwin":
        if not os.path.exists(AIRPORT):
            raise OSError("macOS no longer ships the 'airport' tool (removed in macOS 14.4); "
                          "use --from-file with a saved `system_profiler` or airport output")
        command = [AIRPORT, "-I"]
    else:
        command = ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,CHAN,FREQ,SECURITY", "dev", "wifi"]
    try:
        result = run(command, capture_output=True, text=True, timeout=30, check=False)
    except FileNotFoundError:
        raise OSError(f"'{command[0]}' is not installed on this system") from None
    if result.returncode:
        raise OSError((result.stderr.strip().splitlines() or [f"{command[0]} failed"])[-1])
    return result.stdout


def describe(wifi):
    percent = wifi["signal_percent"]
    lines = [f"Network:   {wifi['ssid']}"]
    if percent is not None:
        dbm = f" ({wifi['rssi_dbm']} dBm)" if wifi.get("rssi_dbm") is not None else ""
        lines.append(f"Signal:    {percent}% {quality(percent)}{dbm}")
    for label, key, unit in (("Band", "band", ""), ("Channel", "channel", ""),
                             ("Security", "security", ""), ("Speed", "rate_mbps", " Mbit/s"),
                             ("Radio", "radio", ""), ("BSSID", "bssid", "")):
        if wifi.get(key) not in (None, ""):
            lines.append(f"{label + ':':<10} {wifi[key]}{unit}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report the current Wi-Fi connection.")
    parser.add_argument("--from-file", type=Path, dest="source",
                        help="saved `netsh wlan show interfaces`, airport -I or nmcli output")
    parser.add_argument("--nearby", action="store_true", help="also list other networks (nmcli)")
    parser.add_argument("--min-signal", type=int, help="exit 1 if the signal is below this %%")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    try:
        text = (args.source.read_text(encoding="utf-8") if args.source else read_system())
        current, others = parse_any(text)
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as err:
        print(f"Can't read the Wi-Fi details: {err}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps({"connected": current is not None, "current": current,
                          "nearby": others if args.nearby else None}, indent=1))
    elif current:
        print(describe(current))
    else:
        print("Not connected to a Wi-Fi network.")
    if args.format == "text" and args.nearby:
        if others:
            print("\nNearby networks:")
            for n in sorted(others, key=lambda n: -(n["signal_percent"] or 0)):
                print(f"  {n['ssid']:<24} {n['signal_percent']:>3}%  {n['band'] or '':<8} "
                      f"{n['security']}")
        else:
            print("\nNo other networks listed (only nmcli on Linux lists them).")
    if current is None:
        return 1
    low = args.min_signal is not None and (current["signal_percent"] or 0) < args.min_signal
    if low:
        print(f"Signal {current['signal_percent']}% is below the {args.min_signal}% minimum.",
              file=sys.stderr)
    return 1 if low else 0


if __name__ == "__main__":
    sys.exit(main())
