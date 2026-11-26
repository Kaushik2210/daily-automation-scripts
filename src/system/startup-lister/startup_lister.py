"""List the programs that start automatically with the OS (Windows, macOS and Linux)."""
import argparse
import csv
import json
import os
import plistlib
import sys
from pathlib import Path

RUN_KEYS = [("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run"),
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
            ("HKLM", r"Software\Microsoft\Windows\CurrentVersion\Run"),
            ("HKLM", r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run")]
STARTUP_TYPES = (".lnk", ".cmd", ".bat", ".exe", ".vbs", ".ps1")
RISKY_PLACES = ("\\temp\\", "/tmp/", "\\downloads\\", "/downloads/", "\\appdata\\local\\temp",
                "$recycle.bin")


def item(source, name, command, enabled=True, where=""):
    return {"source": source, "name": name, "command": command, "enabled": enabled,
            "location": str(where)}


def parse_desktop(text):
    """Key=value pairs from the [Desktop Entry] section of a .desktop file."""
    values, inside = {}, False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("["):
            inside = line == "[Desktop Entry]"
        elif inside and "=" in line and not line.startswith("#"):
            key, _, value = line.partition("=")
            values.setdefault(key.strip(), value.strip())
    return values


def scan_desktop_dir(folder, label):
    found = []
    for path in sorted(Path(folder).glob("*.desktop")):
        try:
            values = parse_desktop(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        off = (values.get("Hidden", "").lower() == "true"
               or values.get("X-GNOME-Autostart-enabled", "").lower() == "false")
        found.append(item(label, values.get("Name", path.stem), values.get("Exec", ""),
                          not off, path))
    return found


def scan_plist_dir(folder, label):
    found = []
    for path in sorted(Path(folder).glob("*.plist")):
        try:
            data = plistlib.loads(path.read_bytes())
        except (OSError, plistlib.InvalidFileException, ValueError):
            continue
        args = data.get("ProgramArguments") or ([data["Program"]] if data.get("Program") else [])
        at_login = bool(data.get("RunAtLoad") or data.get("KeepAlive"))
        found.append(item(label, data.get("Label", path.stem), " ".join(map(str, args)),
                          at_login and not data.get("Disabled"), path))
    return found


def scan_startup_folder(folder, label):
    found = []
    for path in sorted(Path(folder).glob("*")):
        if path.is_file() and path.suffix.lower() in STARTUP_TYPES:
            found.append(item(label, path.stem, str(path), True, path))
    return found


def read_run_keys(winreg):
    """Read the Windows Run keys through an injectable winreg module."""
    roots = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
    found = []
    for root, subkey in RUN_KEYS:
        try:
            with winreg.OpenKey(roots[root], subkey) as key:
                index = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    found.append(item(f"registry {root}\\{subkey.split(chr(92))[-1]}", name,
                                      str(value), True, f"{root}\\{subkey}"))
                    index += 1
        except OSError:
            continue  # the key doesn't exist or can't be read
    return found


def scan_root(root):
    """A home-style folder: .config/autostart, Library/LaunchAgents and Startup."""
    root = Path(root)
    items = []
    for sub, scan, label in ((".config/autostart", scan_desktop_dir, "autostart (desktop)"),
                             ("Library/LaunchAgents", scan_plist_dir, "launchd agent"),
                             ("Startup", scan_startup_folder, "startup folder")):
        if (root / sub).is_dir():
            items += scan(root / sub, label)
    return items


def scan_system():
    home = Path.home()
    items = scan_root(home)
    items += scan_desktop_dir("/etc/xdg/autostart", "autostart (system)") \
        if Path("/etc/xdg/autostart").is_dir() else []
    for folder, label in (("/Library/LaunchAgents", "launchd agent (all users)"),
                          ("/Library/LaunchDaemons", "launchd daemon")):
        if Path(folder).is_dir():
            items += scan_plist_dir(folder, label)
    if os.name == "nt":
        import winreg
        items += read_run_keys(winreg)
        for base in (os.environ.get("APPDATA"), os.environ.get("PROGRAMDATA")):
            startup = Path(base or "") / "Microsoft/Windows/Start Menu/Programs/Startup"
            if base and startup.is_dir():
                items += scan_startup_folder(startup, "startup folder")
    return items


def is_risky(command):
    return any(place in command.lower() for place in RISKY_PLACES)


def main(argv=None):
    parser = argparse.ArgumentParser(description="List programs that start with the OS.")
    parser.add_argument("--root", type=Path,
                        help="scan this folder like a home folder (.config/autostart, "
                             "Library/LaunchAgents, Startup) instead of the real system")
    parser.add_argument("--only-enabled", action="store_true", help="hide disabled entries")
    parser.add_argument("--format", choices=["text", "json", "csv"], default="text")
    args = parser.parse_args(argv)
    if args.root and not args.root.is_dir():
        print(f"Not a folder: {args.root}", file=sys.stderr)
        return 1
    items = scan_root(args.root) if args.root else scan_system()
    if args.only_enabled:
        items = [i for i in items if i["enabled"]]
    for entry in items:
        entry["risky"] = is_risky(entry["command"])
    if args.format == "json":
        print(json.dumps(items, indent=1))
        return 0
    if args.format == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=["source", "name", "command", "enabled",
                                                        "risky", "location"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(items)
        return 0
    if not items:
        print("No startup items found.")
        return 0
    for source in dict.fromkeys(i["source"] for i in items):
        group = [i for i in items if i["source"] == source]
        print(f"{source} ({len(group)})")
        for entry in group:
            flags = ("" if entry["enabled"] else "  [disabled]") + (
                "  [runs from a temp or downloads folder]" if entry["risky"] else "")
            print(f"  {entry['name']}: {entry['command'] or '(no command)'}{flags}")
        print()
    on = sum(i["enabled"] for i in items)
    print(f"{len(items)} item(s), {on} enabled, {len(items) - on} disabled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
