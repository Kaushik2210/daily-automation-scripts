# video-frame-grabber

## Purpose
Turn a video into a set of still pictures: one frame every N seconds, for thumbnails, storyboards, slides from a recorded talk or a quick visual summary. It uses FFmpeg to seek straight to each moment, so it is fast even on long videos, and it names each picture with its timestamp.

## Install
Needs FFmpeg (including `ffprobe`) on your PATH: `winget install ffmpeg`, `brew install ffmpeg` or `sudo apt install ffmpeg`. No Python packages are required.

## Usage
```bash
python video_frame_grabber.py VIDEO [--every 10] [--start 0] [--count N] [--format jpg|png] [-o OUTDIR] [--apply]
```
Dry run by default: it works out the timestamps and file names and shows the plan without running FFmpeg. With `--apply` the frames are saved into `./frames` (or `-o`). `--duration SECONDS` tells the tool the video's length so the plan works without `ffprobe`. Existing frames are skipped (FFmpeg is run with `-n`, so nothing is ever overwritten).

## Example
```bash
python video_frame_grabber.py holiday.mp4 --duration 95 --every 30
```
```
holiday.mp4: 0:01:35 long, one frame every 30s
  0:00:00 -> holiday_00000000ms.jpg
  0:00:30 -> holiday_00030000ms.jpg
  0:01:00 -> holiday_00060000ms.jpg
  0:01:30 -> holiday_00090000ms.jpg
Would save 4 frame(s) to frames. Use --apply to do it.
```

## Notes
- Names look like `holiday_00030000ms.jpg` (milliseconds into the video) so they sort in order.
- The last frame is always before the end of the video; a frame at exactly the end would be empty.
- Use `video-info-reporter` to see a video's length and codecs first, and `contact-sheet-maker` to view the frames together.
- The website demo shows the plan; saving real frames works on your own computer.
