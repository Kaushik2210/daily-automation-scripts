# todo-cli

## Purpose
A tiny task list for the terminal: add tasks with a priority, see what is open, tick things off. High-priority tasks float to the top.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python todo_cli.py add TEXT... [-p high|normal|low]
python todo_cli.py list [--all]
python todo_cli.py done NUMBER...      # also: undo, remove
python todo_cli.py clear-done
```
Tasks are stored in a small JSON file (default `~/.todos.json`, change it with `--file`). That file is the tool's own storage, so changes are saved straight away.

## Example
```bash
python todo_cli.py list --file todos.json
```
```
[ ]   1 ! Write the weekly report
[ ]   4 ! Renew passport
[ ]   2   Book dentist appointment
[x]   3   Reply to Sam
3 open, 1 done.
```

## Notes
- `!` marks open high-priority tasks. Task numbers never get reused.
- `list` hides finished tasks unless you pass `--all`.
- An unknown task number stops with an error and exit code 1.
