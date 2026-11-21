# text-expander

## Purpose
Type less. Define short abbreviations once (`btw` for "by the way", `;sig` for your signature, `addr` for your address) and the tool expands them everywhere in your text files. Abbreviations are matched as whole words, longer ones win over shorter ones, and the replacement can span several lines and include `{date}`, `{time}` or `{datetime}`.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python text_expander.py FILE [FILE ...] --map abbreviations.txt [--ignore-case] [--apply]
```
The map file has one `abbreviation = replacement` per line (use `\n` for a line break; `#` starts a comment), or it can be a JSON object. **Dry run by default:** each file is reported with the number of replacements and the first changed line; add `--apply` to rewrite the files. Before changing a file the tool saves a backup next to it (`note.txt.bak`, or a time-stamped one if that exists), so you can always go back.

## Example
```bash
python text_expander.py expand-demo.txt --map expander-map.txt
```
```
{{OUTPUT}}
```

## Notes
- Matching is case-sensitive unless you pass `--ignore-case`.
- An abbreviation inside a longer word is left alone (`btw` doesn't change `abtwx`), and so is text like `;sig2`.
- Use `snippet-manager` to keep longer reusable text and copy it to the clipboard.
