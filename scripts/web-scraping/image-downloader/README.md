# image-downloader

## Purpose
Grab every picture from a page in one go. The tool finds the images on a web page (normal `<img>` tags, lazy-loaded images, responsive `srcset` lists and the social preview image), works out the full web address of each, and downloads them into a folder. Without `--apply` it only lists what it would fetch.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python image_downloader.py SOURCE [--out images] [--ext jpg --ext png] [--limit 100] [--base URL] [--apply]
```
`SOURCE` is a page URL or a saved `.html` file (add `--base` so relative links can be resolved). From a `srcset` it picks the largest version. Tiny inline `data:` images are ignored. Files that already exist are never overwritten: a copy gets a number (`photo-2.jpg`).

## Example
```bash
python image_downloader.py gallery.html --base https://example.com/shop/ --ext jpg --ext webp
```
```
1. would download https://cdn.example.com/cover.jpg
  2. would download https://example.com/img/a.jpg
  3. would download https://example.com/img/lazy.webp
  4. would download https://example.com/img/large.jpg
4 image(s) found. Dry run - add --apply to download them to images.
```

## Notes
- Each image is limited to 20 MB, and a run stops at `--limit` images (100 by default).
- Responses that aren't images, such as an HTML error page, are reported and skipped.
- Check that you're allowed to reuse the pictures. Downloading is easy; copyright still applies.
- The website demo can only list images from saved files; downloading works on your own computer.
