# glossary-builder

## Purpose
Turn your study notes or documentation into a glossary. Write definitions as you go in the form `**Term**: what it means` (or `**Term** - what it means`, with or without a leading bullet) and the tool gathers them from one or more markdown files into an alphabetical glossary grouped by letter. Terms defined twice are merged, and bold words that have no definition are counted so you know what is left to explain.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python glossary_builder.py NOTES.md [MORE.md ...] [--format md|csv|json] [--include-undefined] [-o glossary.md]
```
The result is printed unless you give `-o` (which refuses to overwrite an existing file). `--include-undefined` also lists bold terms that have no definition, marked "(no definition yet)". Text in code blocks is ignored. The exit code is 1 if no definitions were found.

## Example
```bash
python glossary_builder.py study-notes.md --include-undefined
```
```
{{OUTPUT}}
```

## Notes
- When a term is defined more than once, the first definition is kept and a note says so.
- Terms are matched without regard to capital letters.
- CSV and JSON output are handy for flashcard apps and spreadsheets.
