# json-pretty-printer

## Purpose
Make JSON readable, shrink it, or just find out whether it is valid. When parsing fails it shows the offending line with a pointer to the exact column.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python json_pretty_printer.py [FILE] [--indent N] [--sort-keys] [--minify] [--check]
                              [-o OUTPUT --apply]
```
With no file it reads standard input. Output goes to the terminal; writing a file needs both `-o` and `--apply`.

## Example
```bash
echo '{"b": 1, "a": [1, 2]}' | python json_pretty_printer.py --sort-keys
```
```
{
  "a": [
    1,
    2
  ],
  "b": 1
}
```

## Notes
- Exit code 1 means the JSON was invalid, which is handy in scripts and pre-commit hooks.
- Non-ASCII characters are kept as they are, not escaped.
