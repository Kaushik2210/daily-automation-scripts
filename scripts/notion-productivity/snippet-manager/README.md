# snippet-manager

## Purpose
Keep the text you type again and again (email replies, your address, SQL queries, code) in one place and get it back in a second. Save a snippet with a name, then `copy` it to the clipboard and paste it anywhere. Snippets can contain `{date}`, `{time}` and `{datetime}` placeholders that are filled in when you show or copy them, and the tool counts how often you use each one.

## Install
Standard library only, Python 3.11+. Copying uses your system's clipboard tool: `clip` on Windows, `pbcopy` on macOS, and `wl-copy`, `xclip` or `xsel` on Linux. If none is found, the text is printed instead.

## Usage
```bash
python snippet_manager.py add NAME "text to save" [--file FILE] [--overwrite]
python snippet_manager.py list
python snippet_manager.py show NAME
python snippet_manager.py copy NAME
python snippet_manager.py search WORD
python snippet_manager.py delete NAME [--apply]
```
Snippets live in `snippets.json` in your home folder, or the file you give with `--store`. `add` refuses to replace an existing snippet unless you pass `--overwrite`. `delete` only says what it would remove until you add `--apply`. A mistyped name suggests close matches.

## Example
```bash
python snippet_manager.py list --store snippets.json
```
```
address               39 chars  used 4x  Kaushik 12 Park Street Bengaluru 560001
meeting-reply         90 chars  used 9x  Thanks for the invite. I can join on {date} at {ti
sig                   37 chars  used 31x  Best regards, Kaushik svk@example.com
sql-active            62 chars  used 2x  SELECT * FROM users WHERE active = 1 ORDER BY crea

4 snippet(s) in snippets.json.
```

## Notes
- The store is a readable JSON file, easy to back up or sync with a cloud folder.
- Use `text-expander` if you'd rather type short abbreviations that expand inside text files.
- The website demo lists and shows saved snippets; copying to the clipboard works on your own computer.
