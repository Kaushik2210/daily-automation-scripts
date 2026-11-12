"""Show the end of a log file and keep following it, printing only lines that match a filter."""
import argparse
import re
import sys
import time
from pathlib import Path

LEVELS = ["TRACE", "DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL"]
CANONICAL = {"WARN": "WARNING", "ERR": "ERROR", "FATAL": "CRITICAL", "SEVERE": "CRITICAL"}
LEVEL = re.compile(r"\b(TRACE|DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|ERR|CRITICAL|FATAL|SEVERE)\b",
                   re.IGNORECASE)


class LineFilter:
    """Decides which lines to show: a pattern to include, patterns to drop, a minimum level."""

    def __init__(self, include=None, exclude=(), min_level=None):
        self.include, self.exclude, self.min_level = include, list(exclude), min_level

    def level(self, line):
        match = LEVEL.search(line)
        if not match:
            return None
        name = match.group(1).upper()
        return CANONICAL.get(name, name)

    def accepts(self, line):
        if self.include and not self.include.search(line):
            return False
        if any(p.search(line) for p in self.exclude):
            return False
        if self.min_level:
            found = self.level(line)
            if found is None or LEVELS.index(found) < LEVELS.index(self.min_level):
                return False
        return True


def last_lines(path, count, block=8192):
    """The last `count` lines of a file, read from the end so big files are quick."""
    if count <= 0:
        return []
    with path.open("rb") as handle:
        handle.seek(0, 2)
        position, data = handle.tell(), b""
        while position > 0 and data.count(b"\n") <= count:
            step = min(block, position)
            position -= step
            handle.seek(position)
            data = handle.read(step) + data
    lines = data.decode("utf-8", errors="replace").splitlines()
    return lines[-count:]


def follow(path, line_filter, emit, interval=0.5, max_seconds=None, max_matches=None,
           clock=time.monotonic, sleep=time.sleep):
    """Print new matching lines as they are appended. Returns how many lines matched."""
    started, matched, buffer = clock(), 0, ""
    handle = path.open("r", encoding="utf-8", errors="replace")
    try:
        handle.seek(0, 2)
        while True:
            chunk = handle.read()
            if chunk:
                buffer += chunk
                *complete, buffer = buffer.split("\n")
                for line in complete:
                    if line_filter.accepts(line):
                        emit(line)
                        matched += 1
                        if max_matches and matched >= max_matches:
                            return matched
                continue
            try:
                if path.stat().st_size < handle.tell():  # the log was rotated or emptied
                    handle.seek(0)
                    buffer = ""
                    continue
            except OSError:
                pass  # briefly missing during rotation; keep waiting
            if max_seconds is not None and clock() - started >= max_seconds:
                return matched
            sleep(interval)
    finally:
        handle.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Follow a log file and filter by pattern.")
    parser.add_argument("file", type=Path, help="the log file")
    parser.add_argument("-p", "--pattern", help="only show lines matching this regex")
    parser.add_argument("-x", "--exclude", action="append", default=[], metavar="REGEX",
                        help="hide lines matching this regex (repeat for several)")
    parser.add_argument("-i", "--ignore-case", action="store_true", help="ignore case in patterns")
    parser.add_argument("--level", choices=LEVELS, help="only this level and above")
    parser.add_argument("-n", "--lines", type=int, default=10,
                        help="matching lines to show from the end first (10)")
    parser.add_argument("--no-follow", action="store_true", help="show the end, then stop")
    parser.add_argument("--max-seconds", type=float, help="stop following after this long")
    parser.add_argument("--max-matches", type=int, help="stop after this many new matches")
    parser.add_argument("--interval", type=float, default=0.5, help="seconds between checks (0.5)")
    args = parser.parse_args(argv)
    if args.lines < 0:
        parser.error("--lines can't be negative")
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")
    flags = re.IGNORECASE if args.ignore_case else 0
    try:
        line_filter = LineFilter(re.compile(args.pattern, flags) if args.pattern else None,
                                 [re.compile(p, flags) for p in args.exclude], args.level)
    except re.error as err:
        parser.error(f"bad pattern: {err}")

    # Take more lines than asked for, since some of them will be filtered out.
    shown = []
    if args.lines:
        window = last_lines(args.file, max(args.lines * 50, 500))
        shown = [line for line in window if line_filter.accepts(line)][-args.lines:]
    for line in shown:
        print(line)
    if args.no_follow:
        return 0 if shown else 1
    print(f"-- following {args.file} (Ctrl+C to stop) --", file=sys.stderr, flush=True)
    try:
        follow(args.file, line_filter, lambda line: print(line, flush=True), args.interval,
               args.max_seconds, args.max_matches)
    except KeyboardInterrupt:
        pass
    except OSError as err:
        print(f"Couldn't follow the file: {err.strerror or err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
