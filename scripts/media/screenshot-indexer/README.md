# screenshot-indexer

## Purpose
Find a screenshot by what is written in it. The tool builds a small search index of a folder of screenshots (size, date from the file name, and the text visible in the picture) and lets you search it later: `search "invoice 4821"` lists every screenshot containing those words, with a snippet of the text. Re-indexing is incremental, so only new or changed pictures are processed.

## Install
Needs Pillow:
```bash
pip install -r requirements.txt
```
For the text, the tool uses (in this order) a **sidecar file** next to the picture (`shot.png.txt` or `shot.txt`, with text from any OCR program or app) or, if [Tesseract](https://github.com/tesseract-ocr/tesseract) is installed and on your PATH, runs it for you. Without either, pictures are still indexed by name, size and date, but not by their text.

## Usage
```bash
python screenshot_indexer.py index FOLDER [--index screenshots-index.json] [--apply]
python screenshot_indexer.py search "words to find" [--index screenshots-index.json]
```
`index` is a dry run until you add `--apply`, which writes the JSON index. `search` needs every word to appear (in the text or the file name) and exits with 1 when nothing matches. Pictures that disappeared from the folder stay in the index until you delete the index file.

## Example
```bash
python screenshot_indexer.py index screenshots/ --index shots-index.json --apply
```
```
{{OUTPUT}}
```

## Notes
- OCR is never perfect; search for distinctive words rather than whole sentences.
- The index contains the text of your screenshots, which may include private information; keep it private.
- The website demo reads the sidecar text files; Tesseract OCR runs on your own computer.
