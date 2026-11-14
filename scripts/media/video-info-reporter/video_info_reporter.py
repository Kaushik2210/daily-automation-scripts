"""Report codec, resolution, size and duration of video files using ffprobe."""
import argparse
import json
import shutil
import subprocess  # web-ok: ffprobe is only run for real video files; --from-json works anywhere
import sys
from pathlib import Path

EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".flv", ".wmv", ".mpg", ".mpeg"}


def probe(path):
    """Run ffprobe and return its JSON (raises OSError / ValueError on trouble)."""
    exe = shutil.which("ffprobe")
    if not exe:
        raise OSError("ffprobe was not found - install FFmpeg (https://ffmpeg.org)")
    result = subprocess.run([exe, "-v", "error", "-print_format", "json", "-show_format",
                             "-show_streams", str(path)], capture_output=True, text=True,
                            timeout=60, check=False)
    if result.returncode:
        lines = result.stderr.strip().splitlines()
        raise ValueError(lines[-1] if lines else "ffprobe failed")
    return json.loads(result.stdout)


def fps(rate):
    try:
        top, _, bottom = rate.partition("/")
        value = float(top) / float(bottom or 1)
    except (ValueError, ZeroDivisionError):
        return None
    return f"{value:.3f}".rstrip("0").rstrip(".") if value else None


def clock(seconds):
    seconds = round(seconds)
    hours, rest = divmod(seconds, 3600)
    return f"{hours}:{rest // 60:02d}:{rest % 60:02d}" if hours else f"{rest // 60}:{rest % 60:02d}"


def human(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def summarise(data):
    """Turn ffprobe JSON into (list of label/value rows)."""
    fmt, streams = data.get("format", {}), data.get("streams", [])
    rows = []
    if fmt.get("duration"):
        rows.append(("Duration", clock(float(fmt["duration"]))))
    if fmt.get("size"):
        rows.append(("Size", human(int(fmt["size"]))))
    if fmt.get("bit_rate"):
        rows.append(("Bitrate", f"{int(fmt['bit_rate']) // 1000} kbps overall"))
    for stream in streams:
        kind = stream.get("codec_type")
        if kind == "video":
            size = f"{stream.get('width')}x{stream.get('height')}"
            detail = [stream.get("codec_name", "?"), size]
            frame_rate = fps(stream.get("avg_frame_rate") or stream.get("r_frame_rate", ""))
            if frame_rate:
                detail.append(f"{frame_rate} fps")
            if stream.get("pix_fmt"):
                detail.append(stream["pix_fmt"])
            rows.append(("Video", ", ".join(detail)))
        elif kind == "audio":
            detail = [stream.get("codec_name", "?")]
            if stream.get("sample_rate"):
                detail.append(f"{int(stream['sample_rate']) / 1000:g} kHz")
            detail.append(stream.get("channel_layout") or f"{stream.get('channels', '?')} ch")
            rows.append(("Audio", ", ".join(detail)))
        elif kind == "subtitle":
            rows.append(("Subtitles", stream.get("codec_name", "?")))
    for key in ("title", "creation_time"):
        if fmt.get("tags", {}).get(key):
            rows.append((key.replace("_", " ").capitalize(), fmt["tags"][key]))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report video details using ffprobe.")
    parser.add_argument("paths", nargs="*", type=Path, help="video files or folders")
    parser.add_argument("--from-json", type=Path, action="append", default=[],
                        help="read saved 'ffprobe -print_format json' output instead")
    args = parser.parse_args(argv)
    if not args.paths and not args.from_json:
        parser.error("give video files/folders, or --from-json")

    jobs = []
    for path in args.paths:
        if path.is_dir():
            jobs += [(p.name, p, False) for p in sorted(path.iterdir())
                     if p.suffix.lower() in EXTENSIONS]
        elif path.is_file():
            jobs.append((path.name, path, False))
        else:
            print(f"not found: {path}", file=sys.stderr)
    jobs += [(p.name, p, True) for p in args.from_json]
    if not jobs:
        print("No video files found.", file=sys.stderr)
        return 1

    failures, total = 0, 0.0
    for name, path, saved in jobs:
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if saved else probe(path)
            rows = summarise(data)
        except (OSError, ValueError, subprocess.TimeoutExpired) as err:
            print(f"{name}: can't read it ({err})")
            failures += 1
            continue
        label = data.get("format", {}).get("filename") or name
        print(Path(label).name if saved else name)
        for key, value in rows:
            print(f"  {key:<10} {value}")
        total += float(data.get("format", {}).get("duration") or 0)
    print(f"\n{len(jobs) - failures} video(s), {clock(total)} in total.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
