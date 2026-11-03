# gif-frame-extractor

## Purpose
Split an animated GIF into its individual frames, for editing, sprite sheets or just looking at one moment. It also tells you how many frames there are and how long each one lasts.

## Install
Needs Pillow:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python gif_frame_extractor.py FILE.gif [--format png|jpg|webp] [-o OUTDIR] [--apply]
```
Dry run by default: it lists the frames it would write. Pass `--apply` to write them into `OUTDIR` (default `<name>_frames` next to the GIF).

## Example
```bash
python gif_frame_extractor.py loading.gif --apply
```
```
loading.gif: 4 frame(s), 480 ms in total
  loading_frame001.png  (120 ms)
  loading_frame002.png  (120 ms)
  loading_frame003.png  (120 ms)
  loading_frame004.png  (120 ms)
Wrote 4 frame(s) to loading_frames.
```

## Notes
- A still (non-animated) image counts as one frame.
- `jpg` output has no transparency; PNG and WEBP keep it.
- The GIF itself is never modified.
