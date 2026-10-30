# line-deduper

## Purpose
Remove repeated lines from a file or a pipe without reordering the rest, unlike `sort -u`.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python line_deduper.py [FILE] [-i] [--strip] [-o OUTPUT]
```
With no file it reads standard input. The result goes to standard output unless `-o` is given.

## Example
```bash
printf "pear\napple\npear\nApple\n" | python line_deduper.py -i
```
```
pear
apple
Removed 2 duplicate line(s).
```

## Notes
- The input file is never modified; write to `-o` or redirect the output.
- The count of removed lines is printed to stderr so it won't pollute piped output.
