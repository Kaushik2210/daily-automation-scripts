# tree-printer

## Purpose
Print a folder as a tree, handy for pasting into docs, issues or chat. Works the same on Windows, macOS and Linux.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python tree_printer.py [FOLDER] [-d DEPTH] [-a] [--dirs-only] [--ascii]
```

## Example
```bash
python tree_printer.py ./myapp -d 2
```
```
myapp
├── src
│   ├── pkg
│   └── main.py
├── tests
└── README.md
```

## Notes
- Folders are listed before files, each group sorted by name.
- Hidden entries are skipped unless you pass `-a`.
- If the terminal can't display box-drawing characters, the script falls back to ASCII automatically.
- Symlinked folders are shown but not followed.
