# word-counter

## Purpose
Count lines, words, characters and bytes in one or more text files, and optionally list the most common words.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python word_counter.py [FILE ...] [--top N]
```
With no files it reads from standard input, so it works in a pipe.

## Example
```bash
python word_counter.py essay.txt notes.txt --top 3
```
```
   lines   words     chars     bytes  file
     120    2310     13840     13902  essay.txt
      34     410      2388      2388  notes.txt

Most common words:
    58  the
    31  and
    22  that
```

## Notes
- Words in the top list are lowercased and must be at least 3 letters long.
- Files that can't be read are reported on stderr and skipped.
- Read-only.
