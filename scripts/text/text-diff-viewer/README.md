# text-diff-viewer

## Purpose
See what changed between two versions of a text file, as a unified diff, with colour when your terminal supports it.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python text_diff_viewer.py OLD NEW [-c LINES] [--color auto|always|never] [--exit-code]
```

## Example
```bash
python text_diff_viewer.py notes_v1.txt notes_v2.txt
```
```
--- notes_v1.txt
+++ notes_v2.txt
@@ -1,3 +1,3 @@
 buy milk
-call mum
+call dad
 pay rent

83% similar
```

## Notes
- Colour is on automatically in a terminal and off when piping to a file.
- The script exits with 0 even when files differ, unless you pass `--exit-code` (then 1 means different).
- Read-only.
