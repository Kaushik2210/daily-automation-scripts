# video-info-reporter

## Purpose
Get the key facts about video files in one glance: duration, file size, overall bitrate, the video codec with its resolution, frame rate and pixel format, the audio codec with sample rate and channel layout, subtitles, and the title/creation date if the file has them. It asks FFmpeg's `ffprobe` for the data, so it understands virtually every format.

## Install
Needs FFmpeg (which includes `ffprobe`) on your PATH: `winget install ffmpeg`, `brew install ffmpeg` or `sudo apt install ffmpeg`. No Python packages are required.

## Usage
```bash
python video_info_reporter.py FILE_OR_FOLDER [...]
python video_info_reporter.py --from-json probe.json
```
Folders are scanned for common video extensions. `--from-json` reads output you saved earlier with `ffprobe -v error -print_format json -show_format -show_streams video.mp4 > probe.json`, which is useful on a machine without FFmpeg. The exit code is 1 if any file couldn't be read.

## Example
```bash
python video_info_reporter.py --from-json ffprobe-holiday.json
```
```
holiday.mp4
  Duration   2:05
  Size       73.6 MB
  Bitrate    4922 kbps overall
  Video      h264, 1920x1080, 29.97 fps, yuv420p
  Audio      aac, 48 kHz, stereo
  Title      Holiday in Goa
  Creation time 2026-03-01T09:30:15.000000Z

1 video(s), 2:05 in total.
```

## Notes
- If `ffprobe` isn't installed the tool says so instead of crashing.
- Use `video-frame-grabber` to save pictures from a video.
- The website demo reads saved ffprobe output; real videos are analysed on your own computer.
