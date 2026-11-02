# base64-tool

## Purpose
Encode or decode Base64, for example to inspect a token, embed a small file in a config, or turn a binary file into text and back. Supports both the standard and the URL-safe alphabets.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python base64_tool.py [TEXT] [-f FILE] [-d] [--url-safe] [-o OUTPUT --apply]
```
Input comes from the text argument, `--file`, or standard input. Add `-d` to decode. Text results are printed; binary results need `-o FILE --apply` so they aren't dumped into your terminal.

## Example
```bash
python base64_tool.py "hello world"
python base64_tool.py -d aGVsbG8gd29ybGQ=
```
```
aGVsbG8gd29ybGQ=
hello world
```

## Notes
- Base64 is an encoding, not encryption. Anyone can decode it, so never use it to hide secrets.
- Decoding ignores whitespace and accepts input without `=` padding.
- Invalid input exits with code 1 and a message.
