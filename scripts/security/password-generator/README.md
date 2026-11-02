# password-generator

## Purpose
Create strong random passwords or easy-to-type passphrases. It uses Python's `secrets` module, which draws from the operating system's secure random source, not the ordinary `random` module.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python password_generator.py [-n COUNT] [-l LENGTH] [--no-symbols] [--no-ambiguous]
python password_generator.py --passphrase WORDS [--separator CHAR] [-n COUNT]
```
Passwords always contain a lowercase letter, an uppercase letter, a digit and (unless turned off) a symbol.

## Example
```bash
python password_generator.py -n 2 -l 18
python password_generator.py --passphrase 4
```
```
r7#Kd!mQ2vZ_e8Wb+L
Xp4%tN9hC&uA3sEk@Y
Maple-Cafe-Wolf-Jade
```

## Notes
- Output goes to the terminal only; nothing is saved or sent anywhere.
- The built-in word list is small (181 words, roughly 7.5 bits per word), so use 6 or more words for passphrases that matter.
- `--no-ambiguous` skips characters that look alike, such as `O`, `0`, `l` and `1`.
