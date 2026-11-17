# srt-shifter

## Purpose
Fix subtitles that appear too early or too late. The tool moves every cue in an `.srt` file by an offset you give (for example 2.5 seconds later, or 1 second earlier), optionally only from a certain time onwards, and writes a new, correctly numbered file. Cues pushed before 00:00:00 are clamped or dropped.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python srt_shifter.py MOVIE.srt --shift 2.5 [--after 00:10:00] [-o OUT.srt] [--apply]
python srt_shifter.py MOVIE.srt --shift=-1.5 --apply
```
Offsets can be `2.5` or `+2.5s` (seconds), `1500ms`, `1m30s` or a clock time such as `00:00:01,500`. For a negative offset write `--shift=-1.5` with an equals sign. `--after` limits the shift to cues starting at or after that time (use it when only the second half is out of sync). Dry run by default: it previews the first cues. With `--apply` it creates `MOVIE.shifted.srt` (or `-o`) and never overwrites an existing file; your original is untouched.

## Example
```bash
python srt_shifter.py subtitles.srt --shift 2.5 --apply
```
```
{{OUTPUT}}
```

## Notes
- Files with Windows line endings or a byte-order mark are handled.
- Only the timings change; the subtitle text is copied as it is.
- If the drift grows over the film (not a fixed offset), the frame rates differ; a stretch factor is outside this tool.
