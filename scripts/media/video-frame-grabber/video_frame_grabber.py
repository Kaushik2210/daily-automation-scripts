"""Save still frames from a video at regular intervals using FFmpeg."""
import argparse
import shutil
import subprocess  # web-ok: FFmpeg only runs with --apply; the dry run plan works anywhere
import sys
from pathlib import Path


def video_duration(video):
    """Length in seconds according to ffprobe."""
    exe = shutil.which("ffprobe")
    if not exe:
        raise OSError("ffprobe was not found - install FFmpeg (https://ffmpeg.org)")
    result = subprocess.run([exe, "-v", "error", "-show_entries", "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", str(video)],
                            capture_output=True, text=True, timeout=60, check=False)
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise ValueError(f"couldn't read the length of {video.name}") from None


def frame_times(duration, every, start=0.0, count=0):
    """Timestamps (seconds) to grab: start, start+every, ... that fall inside the video."""
    times, moment = [], start
    while moment < duration - 0.05 and (not count or len(times) < count):
        times.append(round(moment, 3))
        moment += every
    return times


def frame_name(stem, seconds, ext):
    return f"{stem}_{round(seconds * 1000):08d}ms.{ext}"


def grab_command(video, seconds, target):
    return ["ffmpeg", "-v", "error", "-n", "-ss", f"{seconds:.3f}", "-i", str(video),
            "-frames:v", "1", "-q:v", "2", str(target)]


def clock(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Save frames from a video at intervals.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--every", type=float, default=10, help="seconds between frames (10)")
    parser.add_argument("--start", type=float, default=0, help="first frame at this second (0)")
    parser.add_argument("--count", type=int, default=0, help="stop after this many frames")
    parser.add_argument("--format", choices=["jpg", "png"], default="jpg")
    parser.add_argument("--duration", type=float,
                        help="video length in seconds (skips ffprobe; handy for planning)")
    parser.add_argument("-o", "--outdir", type=Path, help="folder for the frames (default: frames)")
    parser.add_argument("--apply", action="store_true",
                        help="really save the frames (default is a dry run)")
    args = parser.parse_args(argv)
    if args.every <= 0 or args.start < 0 or args.count < 0:
        parser.error("--every must be above 0; --start and --count can't be negative")
    if not args.duration and not args.video.is_file():
        parser.error(f"not a file: {args.video}")

    try:
        duration = args.duration or video_duration(args.video)
    except (OSError, ValueError, subprocess.TimeoutExpired) as err:
        print(f"Can't plan the frames: {err}", file=sys.stderr)
        return 1
    times = frame_times(duration, args.every, args.start, args.count)
    if not times:
        print(f"Nothing to grab: the video is only {clock(duration)} long.", file=sys.stderr)
        return 1
    outdir = args.outdir or Path("frames")
    print(f"{args.video.name}: {clock(duration)} long, one frame every {args.every:g}s")
    saved = failed = 0
    for seconds in times:
        target = outdir / frame_name(args.video.stem, seconds, args.format)
        if target.exists():
            print(f"  skip {target.name}: already exists")
            continue
        print(f"  {clock(seconds)} -> {target.name}")
        if not args.apply:
            continue
        outdir.mkdir(parents=True, exist_ok=True)
        if not shutil.which("ffmpeg"):
            print("ffmpeg was not found - install FFmpeg (https://ffmpeg.org)", file=sys.stderr)
            return 1
        result = subprocess.run(grab_command(args.video, seconds, target), capture_output=True,
                                text=True, timeout=120, check=False)
        if result.returncode or not target.exists():
            print(f"    could not grab this frame: {result.stderr.strip() or 'no output'}")
            failed += 1
        else:
            saved += 1
    if args.apply:
        print(f"Saved {saved} frame(s) to {outdir}" + (f"; {failed} failed." if failed else "."))
        return 1 if failed else 0
    print(f"Would save {len(times)} frame(s) to {outdir}. Use --apply to do it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
