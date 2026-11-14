# similar-image-finder

## Purpose
Find pictures that look the same even though the files differ: a photo and its resized copy, a re-saved or recompressed version, a slightly brightened edit. Exact-duplicate tools miss these because the bytes are different. This one computes a small "perceptual fingerprint" (a 64-bit difference hash) of every image and groups the ones whose fingerprints are nearly identical, marking the largest version of each group.

## Install
Needs Pillow:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python similar_image_finder.py FOLDER [--threshold 6] [-r]
```
`--threshold` is how many of the 64 bits may differ (default 6; 0 means practically identical, higher finds looser matches but also more false alarms). `-r` includes subfolders. The tool only reports: it never moves or deletes anything, so you decide which copies to keep.

## Example
```bash
python similar_image_finder.py similar-demo/
```
```
Group 1: 3 similar images (largest marked *)
 * beach-bright.jpg             640x440  10.2 KB  (reference)
   beach-small.jpg              160x110  2.1 KB  3 bit(s) different
   beach.jpg                    640x440  9.7 KB  2 bit(s) different

Checked 5 image(s): 1 group(s), 2 possible duplicate(s). Nothing was changed.
```

## Notes
- The largest image (by pixels, then file size) is marked `*` as the likely original to keep.
- Cropped or heavily edited versions, or photos of the same scene from a different angle, will not match.
- Use `duplicate-file-finder` for byte-for-byte duplicates.
