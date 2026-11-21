# clipboard-history-logger

## Purpose
Never lose something you copied. The tool watches your clipboard and appends every new piece of text to a history file with a timestamp, then lets you list recent entries or search the whole history ("what was that command I copied on Thursday?"). By default it **skips anything that looks sensitive** (passwords, API keys, private keys, long token-like strings and credit-card numbers) so secrets don't end up in a file.

## Install
Standard library only, Python 3.11+. It uses your system's clipboard tool: PowerShell on Windows, `pbpaste` on macOS, and `wl-paste`, `xclip` or `xsel` on Linux (install one of them).

## Usage
```bash
python clipboard_history_logger.py watch [--log FILE] [--interval 1] [--seconds 600] [--count 20]
python clipboard_history_logger.py list [--last 10]
python clipboard_history_logger.py search TERM
```
`watch` checks the clipboard every `--interval` seconds until you press Ctrl-C (or `--seconds` / `--count` is reached). The history is a JSON-lines file, `clipboard-history.jsonl` in your home folder unless you pass `--log`. `--include-sensitive` turns the secret filter off; `--max-chars` limits how much of each entry is kept. Only text is recorded, not images or files. `search` exits with 1 when nothing matches.

## Example
```bash
python clipboard_history_logger.py search flask --log clipboard-log.jsonl
```
```
2026-11-20 09:12:30  pip install flask requests
2026-11-21 09:20:37  Thanks for the update - I'll review the flask docs tomorrow.

2 match(es) in 7 saved entries.
```

## Notes
- The history file is plain text and unencrypted: anything that passes the filter can be read by anyone with access to your account. Delete it whenever you like.
- The secret filter is a best effort, not a guarantee. Don't rely on it for highly sensitive material.
- The website demo searches a saved history; watching the clipboard works on your own computer.
