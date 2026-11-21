"""Log which application (and window title) has focus over time, to a CSV file."""
import argparse
import contextlib
import csv
import platform
import shutil
import subprocess  # web-ok: only used by `watch` to ask the OS; show works anywhere
import sys
import time
from datetime import datetime
from pathlib import Path

DEFAULT_LOG = Path.home() / "window-log.csv"
FIELDS = ["time", "app", "title"]


def windows_active_window():
    import ctypes
    from ctypes import wintypes

    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    handle = user32.GetForegroundWindow()
    if not handle:
        return "", ""
    buffer = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(handle, buffer, 512)
    title = buffer.value
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
    app = ""
    process = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if process:
        size = wintypes.DWORD(520)
        path = ctypes.create_unicode_buffer(520)
        if kernel32.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size)):
            app = Path(path.value).stem
        kernel32.CloseHandle(process)
    return app, title


def mac_active_window():
    script = ('tell application "System Events"\n'
              "set p to first application process whose frontmost is true\n"
              "set t to \"\"\n"
              "try\nset t to name of front window of p\nend try\n"
              'return (name of p) & "\\t" & t\nend tell')
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True,
                            timeout=10, check=False)
    if result.returncode:
        raise OSError("osascript failed (allow Accessibility access for your terminal)")
    app, _, title = result.stdout.strip("\n").partition("\t")
    return app, title


def linux_active_window():
    if not shutil.which("xdotool"):
        raise OSError("xdotool is required on Linux (and an X11 session); install it first")
    def ask(*args):
        out = subprocess.run(["xdotool", *args], capture_output=True, text=True, timeout=10,
                             check=False)
        return out.stdout.strip() if out.returncode == 0 else ""
    title, pid = ask("getactivewindow", "getwindowname"), ask("getactivewindow", "getwindowpid")
    app = ""
    if pid.isdigit():
        with contextlib.suppress(OSError):
            app = Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip()
    return app, title


def active_window():
    system = platform.system()
    if system == "Windows":
        return windows_active_window()
    if system == "Darwin":
        return mac_active_window()
    return linux_active_window()


def append(log, row):
    fresh = not log.exists() or log.stat().st_size == 0
    with log.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if fresh:
            writer.writeheader()
        writer.writerow(row)


def watch(reader, log, interval, seconds, count, titles, sleep=time.sleep, clock=time.monotonic,
          out=print):
    """Poll the focused window and log each change of window. Returns rows written."""
    written, last, started = 0, None, clock()
    while (not seconds or clock() - started < seconds) and (not count or written < count):
        app, title = reader()
        current = (app, title if titles else "")
        if current != last and (app or title):
            last = current
            row = {"time": datetime.now().isoformat(timespec="seconds"), "app": app,
                   "title": current[1]}
            append(log, row)
            written += 1
            out(f"[{row['time'][11:]}] {app or '?'}" + (f" - {current[1]}" if current[1] else ""))
        sleep(interval)
    return written


def read_log(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("time")]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Log the focused application over time.")
    parser.add_argument("action", choices=["watch", "show"])
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG,
                        help=f"CSV log ({DEFAULT_LOG.name} in your home folder)")
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between checks (2)")
    parser.add_argument("--seconds", type=float, default=0, help="stop after this many seconds")
    parser.add_argument("--count", type=int, default=0, help="stop after this many changes")
    parser.add_argument("--no-titles", action="store_true",
                        help="log only the application, not the window title (more private)")
    parser.add_argument("--last", type=int, default=15, help="rows to show for show (15)")
    args = parser.parse_args(argv)

    if args.action == "watch":
        print(f"Logging the focused window to {args.log} (Ctrl-C to stop)...")
        try:
            written = watch(active_window, args.log, args.interval, args.seconds, args.count,
                            not args.no_titles)
        except OSError as err:
            print(f"Can't read the active window: {err}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print()
            return 0
        print(f"Logged {written} window change(s).")
        return 0
    if not args.log.is_file():
        print(f"No log yet at {args.log}. Run 'watch' first.", file=sys.stderr)
        return 1
    rows = read_log(args.log)
    for row in rows[-args.last:]:
        print(f"{row['time'].replace('T', ' ')}  {row['app']:<14} {row.get('title', '')[:60]}")
    print(f"\nShowing {min(args.last, len(rows))} of {len(rows)} logged window change(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
