"""Log clipboard changes to a searchable file, then list or search the history."""
import argparse
import json
import platform
import re
import shutil
import subprocess  # web-ok: only used by `watch` to read the clipboard; list/search work anywhere
import sys
import time
from datetime import datetime
from pathlib import Path

DEFAULT_LOG = Path.home() / "clipboard-history.jsonl"
READERS = {
    "Windows": [["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"]],
    "Darwin": [["pbpaste"]],
    "Linux": [["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"],
              ["xsel", "--clipboard", "--output"]],
}


def read_clipboard():
    """Return the clipboard text using the tool of this operating system."""
    for command in READERS.get(platform.system(), []):
        if shutil.which(command[0]):
            result = subprocess.run(command, capture_output=True, timeout=10, check=False)
            if result.returncode == 0:
                text = result.stdout.decode("utf-8", errors="replace")
                return text.removesuffix("\r\n") if platform.system() == "Windows" else text
            return ""  # e.g. the clipboard holds an image, not text
    raise OSError("no clipboard tool found (need pbpaste, wl-paste, xclip or xsel)")


def looks_sensitive(text):
    """True for things you probably don't want saved: passwords, keys, card numbers."""
    stripped = text.strip()
    if re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", stripped):
        return True
    if re.search(r"\b(password|passwd|secret|api[_-]?key|token)\b\s*[:=]", stripped, re.IGNORECASE):
        return True
    if re.fullmatch(r"(sk|pk|ghp|gho|xox[bp]|AKIA)[-_A-Za-z0-9]{12,}", stripped):
        return True
    if " " not in stripped and len(stripped) >= 20 and re.search(r"\d", stripped) and re.search(
            r"[A-Za-z]", stripped) and re.fullmatch(r"[A-Za-z0-9+/=_\-]+", stripped):
        return True  # a long unbroken mixed string looks like a token
    digits = re.sub(r"[ -]", "", stripped)
    if digits.isdigit() and 13 <= len(digits) <= 19:
        total = 0
        for index, char in enumerate(reversed(digits)):
            number = int(char) * (2 if index % 2 else 1)
            total += number - 9 if number > 9 else number
        return total % 10 == 0
    return False


def load(log):
    entries = []
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    return entries


def preview(text, width=70):
    flat = " ".join(text.split())
    return flat if len(flat) <= width else flat[:width - 1] + "…"


def watch(reader, log, interval, seconds, count, keep_sensitive, max_chars, sleep=time.sleep,
          clock=time.monotonic, out=print):
    """Poll the clipboard; append each new text to the log. Returns how many were saved."""
    last = reader()  # whatever is there now is not a "change"
    saved, skipped, started = 0, 0, clock()
    while (not seconds or clock() - started < seconds) and (not count or saved < count):
        sleep(interval)
        text = reader()
        if not text or text == last:
            continue
        last = text
        if not keep_sensitive and looks_sensitive(text):
            skipped += 1
            out(f"[{datetime.now():%H:%M:%S}] skipped something that looks sensitive")
            continue
        entry = {"time": datetime.now().isoformat(timespec="seconds"), "length": len(text),
                 "text": text[:max_chars]}
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        saved += 1
        out(f"[{entry['time'][11:]}] {len(text)} chars: {preview(text)}")
    return saved, skipped


def main(argv=None):
    parser = argparse.ArgumentParser(description="Log, list and search clipboard history.")
    parser.add_argument("action", choices=["watch", "list", "search"])
    parser.add_argument("term", nargs="?", help="what to look for (search)")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG,
                        help=f"history file ({DEFAULT_LOG.name} in your home folder)")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds between checks (1)")
    parser.add_argument("--seconds", type=float, default=0, help="stop watching after this long")
    parser.add_argument("--count", type=int, default=0, help="stop after this many entries")
    parser.add_argument("--last", type=int, default=10, help="entries to show for list (10)")
    parser.add_argument("--max-chars", type=int, default=2000, help="longest text to keep (2000)")
    parser.add_argument("--include-sensitive", action="store_true",
                        help="also log text that looks like a password, key or card number")
    args = parser.parse_args(argv)

    if args.action == "watch":
        print(f"Watching the clipboard, logging to {args.log} (Ctrl-C to stop)...")
        try:
            saved, skipped = watch(read_clipboard, args.log, args.interval, args.seconds,
                                   args.count, args.include_sensitive, args.max_chars)
        except OSError as err:
            print(f"Can't read the clipboard: {err}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print()
            return 0
        print(f"Saved {saved} entr{'y' if saved == 1 else 'ies'}"
              + (f", skipped {skipped} sensitive" if skipped else "") + ".")
        return 0

    entries = load(args.log)
    if args.action == "search":
        if not args.term:
            parser.error("search needs something to look for")
        needle = args.term.lower()
        hits = [e for e in entries if needle in e.get("text", "").lower()]
        for entry in hits:
            print(f"{entry['time'].replace('T', ' ')}  {preview(entry['text'])}")
        noun = "entry" if len(entries) == 1 else "entries"
        print(f"\n{len(hits)} match(es) in {len(entries)} saved {noun}.")
        return 0 if hits else 1
    for entry in entries[-args.last:]:
        print(f"{entry['time'].replace('T', ' ')}  {entry.get('length', 0):>5} chars  "
              f"{preview(entry.get('text', ''))}")
    print(f"\nShowing {min(args.last, len(entries))} of {len(entries)} saved entr"
          f"{'y' if len(entries) == 1 else 'ies'} in {args.log.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
