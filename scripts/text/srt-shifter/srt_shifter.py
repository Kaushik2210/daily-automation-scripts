"""Shift subtitle (.srt) timings forward or backward by an offset."""
import argparse
import re
import sys
from pathlib import Path

TIMES = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")


def to_ms(h, m, s, ms):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms.ljust(3, "0"))


def fmt(ms):
    ms = max(0, round(ms))
    hours, rest = divmod(ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    return f"{hours:02d}:{minutes:02d}:{rest // 1000:02d},{rest % 1000:03d}"


def parse_offset(text):
    """'+2.5', '-1.2s', '1500ms', '-1m30s' or '-00:00:01,500' -> milliseconds."""
    text = text.strip().lower().replace(" ", "")
    sign = -1 if text.startswith("-") else 1
    body = text.lstrip("+-")
    clock = re.fullmatch(r"(?:(\d+):)?(\d+):(\d+)(?:[,.](\d{1,3}))?", body)
    if clock:
        hours, minutes, seconds, millis = clock.groups()
        return sign * to_ms(hours or 0, minutes, seconds, millis or "0")
    parts = re.fullmatch(r"(?:(\d+(?:\.\d+)?)m(?!s))?(?:(\d+(?:\.\d+)?)(?:s|sec)?)?"
                         r"|(\d+)ms", body)
    if not body or not parts:
        raise ValueError(f"can't understand the offset {text!r}")
    if parts.group(3):
        return sign * int(parts.group(3))
    minutes, seconds = float(parts.group(1) or 0), float(parts.group(2) or 0)
    return sign * round((minutes * 60 + seconds) * 1000)


def parse_srt(text):
    """Return a list of (start ms, end ms, text lines) cues."""
    cues = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").lstrip("﻿").strip()):
        lines = block.split("\n")
        for position, line in enumerate(lines):
            match = TIMES.search(line)
            if match:
                g = match.groups()
                cues.append((to_ms(*g[:4]), to_ms(*g[4:]), lines[position + 1:]))
                break
    return cues


def shift(cues, offset, after=0):
    """Shift cues that start at or after `after`; drop cues that would end before 0."""
    result, dropped = [], 0
    for start, end, lines in cues:
        if start >= after:
            start, end = start + offset, end + offset
        if end <= 0:
            dropped += 1
            continue
        result.append((max(start, 0), end, lines))
    return result, dropped


def render(cues):
    return "\n".join(f"{number}\n{fmt(start)} --> {fmt(end)}\n" + "\n".join(lines) + "\n"
                     for number, (start, end, lines) in enumerate(cues, 1))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Shift .srt subtitle timings.")
    parser.add_argument("srt", type=Path)
    parser.add_argument("--shift", required=True,
                        help="offset such as 2.5, -1.2s, 1500ms or -00:00:01,500 "
                             "(write --shift=-2 for a negative value)")
    parser.add_argument("--after", default="0",
                        help="only shift cues starting at or after this time (default: all)")
    parser.add_argument("-o", "--output", type=Path,
                        help="file to create (default: NAME.shifted.srt)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the file (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.srt.is_file():
        parser.error(f"not a file: {args.srt}")
    try:
        offset = parse_offset(args.shift)
        after = max(parse_offset(args.after), 0) if args.after != "0" else 0
    except ValueError as err:
        parser.error(str(err))

    cues = parse_srt(args.srt.read_text(encoding="utf-8-sig", errors="replace"))
    if not cues:
        print("No subtitle cues found.", file=sys.stderr)
        return 1
    shifted, dropped = shift(cues, offset, after)
    print(f"{len(cues)} cue(s), shifting by {offset / 1000:+g}s"
          + (f" from {fmt(after)}" if after else ""))
    for (old_start, _, _), (new_start, _, lines) in list(zip(cues, shifted, strict=False))[:5]:
        print(f"  {fmt(old_start)} -> {fmt(new_start)}  {lines[0] if lines else ''}")
    if len(shifted) > 5:
        print(f"  ... and {len(shifted) - 5} more")
    if dropped:
        print(f"{dropped} cue(s) would end before 00:00:00 and are dropped.")
    output = args.output or args.srt.with_name(f"{args.srt.stem}.shifted.srt")
    if not args.apply:
        print(f"Dry run. Use --apply to write {output.name}.")
        return 0
    if output.exists():
        print(f"{output} already exists; choose another name with -o.", file=sys.stderr)
        return 1
    output.write_text(render(shifted), encoding="utf-8")
    print(f"Saved {output} ({len(shifted)} cue(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
