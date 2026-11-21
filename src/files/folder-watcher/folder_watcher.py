"""Watch a folder and run a command whenever new (or changed) files appear."""
import argparse
import fnmatch
import shlex
import subprocess  # web-ok: commands only run with --apply; the dry run works anywhere
import sys
import time
from pathlib import Path

IGNORED = ["*.tmp", "*.part", "*.crdownload", "*.download", "~*", ".*", "*.swp"]


def scan(folder, pattern, recursive):
    """Return {path: (mtime, size)} for the matching files in the folder."""
    found = {}
    for path in (folder.rglob("*") if recursive else folder.iterdir()):
        if not path.is_file() or any(fnmatch.fnmatch(path.name, p) for p in IGNORED):
            continue
        if not fnmatch.fnmatch(path.name, pattern):
            continue
        stat = path.stat()
        found[path] = (stat.st_mtime, stat.st_size)
    return found


def changes(before, after, events):
    """Return [(path, 'new' or 'changed')] between two scans."""
    result = []
    for path, state in sorted(after.items()):
        if path not in before:
            if events in ("new", "both"):
                result.append((path, "new"))
        elif before[path] != state and events in ("changed", "both"):
            result.append((path, "changed"))
    return result


def build_command(template, path):
    """Split the template into arguments first, then fill in the file (no shell involved)."""
    values = {"path": str(path), "name": path.name, "stem": path.stem,
              "ext": path.suffix.lstrip("."), "dir": str(path.parent)}
    if sys.platform == "win32":  # keep backslashes in paths, but still honour "quoted words"
        parts = [p[1:-1] if len(p) > 1 and p[0] == p[-1] and p[0] in "\"'" else p
                 for p in shlex.split(template, posix=False)]
    else:
        parts = shlex.split(template)
    return [part.format(**values) for part in parts]


def handle(path, kind, template, apply, out=print):
    """Report an event and (with apply) run the command. Returns the exit code or None."""
    out(f"{kind:<7} {path.name}")
    if not template:
        return None
    try:
        command = build_command(template, path)
    except (KeyError, IndexError, ValueError) as err:
        out(f"  can't use the command: {err}")
        return 1
    if not apply:
        out(f"  would run: {' '.join(command)}")
        return None
    try:
        result = subprocess.run(command, check=False, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as err:
        out(f"  failed to run: {err}")
        return 1
    out(f"  exit code {result.returncode}")
    return result.returncode


def watch(folder, pattern, recursive, events, template, apply, interval, seconds, include_existing,
          settle, sleep=time.sleep, clock=time.time, out=print):
    """Poll the folder. Returns the number of events handled."""
    before = {} if include_existing else scan(folder, pattern, recursive)
    handled, started = 0, clock()
    while True:
        after = scan(folder, pattern, recursive)
        quiet = {p: s for p, s in after.items() if clock() - s[0] >= settle}
        waiting = {p: s for p, s in after.items() if p not in quiet}
        visible = {p: s for p, s in quiet.items()}
        for path, kind in changes(before, visible, events):
            handle(path, kind, template, apply, out)
            handled += 1
        before = {**visible, **{p: before[p] for p in waiting if p in before}}
        if seconds is not None and (seconds == 0 or clock() - started >= seconds):
            return handled
        sleep(interval)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a command when files appear in a folder.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--run", help="command to run per file, e.g. \"python convert.py {path}\" "
                                      "({path} {name} {stem} {ext} {dir})")
    parser.add_argument("--pattern", default="*", help="only files matching this, e.g. '*.csv'")
    parser.add_argument("--events", choices=["new", "changed", "both"], default="new")
    parser.add_argument("-r", "--recursive", action="store_true", help="include subfolders")
    parser.add_argument("--include-existing", action="store_true",
                        help="treat files already in the folder as new")
    parser.add_argument("--once", action="store_true", help="check once and stop")
    parser.add_argument("--seconds", type=float, help="stop watching after this many seconds")
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between checks (2)")
    parser.add_argument("--settle", type=float, default=2.0,
                        help="wait until a file hasn't changed for this many seconds (2)")
    parser.add_argument("--apply", action="store_true",
                        help="really run the command (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    if args.interval <= 0 or args.settle < 0:
        parser.error("--interval must be above 0 and --settle can't be negative")

    limit = 0 if args.once else args.seconds
    include = args.include_existing or args.once
    print(f"Watching {args.folder} for {args.events} '{args.pattern}' files"
          + ("" if args.apply or not args.run else " (dry run: commands are only shown)")
          + (" - Ctrl-C to stop" if limit is None else "") + "...")
    try:
        handled = watch(args.folder, args.pattern, args.recursive, args.events, args.run,
                        args.apply, args.interval, limit, include, args.settle)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    print(f"{handled} event(s) handled." + ("" if args.apply or not args.run
                                           else " Use --apply to run the command."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
