# markdown-toc-generator

## Purpose
Create a table of contents with working GitHub-style anchor links from the headings of a markdown file.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python markdown_toc_generator.py FILE [--min-level N] [--max-level N] [--apply]
```
By default the TOC is only printed. With `--apply` it is written into the file between `<!-- TOC -->` and `<!-- /TOC -->` markers, or placed under the first heading if the markers don't exist yet.

## Example
```bash
python markdown_toc_generator.py README.md
```
```
- [Install](#install)
- [Usage](#usage)
  - [Options](#options)
```

## Notes
- Headings inside fenced code blocks are ignored.
- Repeated headings get `-1`, `-2` anchors like GitHub does.
- Defaults to levels 2 and 3, so the page title is not listed.
