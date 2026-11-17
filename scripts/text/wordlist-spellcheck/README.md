# wordlist-spellcheck

## Purpose
Catch typos by checking every word of a document against a list of valid words. Anything not in the list is reported with the lines it appears on and up to three "did you mean" suggestions. Because it uses a plain word list, it is easy to adapt: use a dictionary for your language, add your own names and jargon with `--allow`, and it works the same on Windows, macOS and Linux.

## Install
Standard library only, Python 3.11+. You need a word list: a text file with one word per line. On Linux and macOS the tool finds `/usr/share/dict/words` automatically; otherwise pass `--wordlist` (free lists such as SCOWL or `words_alpha.txt` work well).

## Usage
```bash
python wordlist_spellcheck.py FILE [FILE ...] [--wordlist words.txt] [--allow mine.txt] [--ignore-capitalized]
```
Web addresses, email addresses, `inline code` and ALL-CAPS words are skipped. `--allow` adds extra accepted words and can be repeated. `--ignore-capitalized` skips names and places. The exit code is 1 when unknown words are found.

## Example
```bash
python wordlist_spellcheck.py draft.txt --wordlist wordlist-small.txt
```
```
{{OUTPUT}}
```

## Notes
- The tool only reports; it never edits your file.
- A word list can't judge grammar or the wrong-but-valid word ("their" vs "there").
- The demo list here is tiny on purpose; use a full dictionary for real work.
