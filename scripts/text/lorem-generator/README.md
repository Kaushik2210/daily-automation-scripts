# lorem-generator

## Purpose
Produce placeholder text for mock-ups and tests: a set number of paragraphs, or an exact word count.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python lorem_generator.py [-p PARAGRAPHS] [-s SENTENCES] [-w WORDS] [--seed N] [--no-classic-start]
```

## Example
```bash
python lorem_generator.py -p 1 -s 2 --seed 4
```
```
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quis nulla cillum sint ut duis enim aliqua.
```

## Notes
- The first paragraph starts with the classic "Lorem ipsum dolor sit amet" unless you turn it off.
- Use `--seed` to get the same text every time, which is handy for snapshot tests.
- `-w` ignores paragraphs and sentences and prints exactly that many words.
