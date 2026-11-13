# breach-password-checker

## Purpose
Find out whether a password has already leaked, without handing it to anyone. The tool uses the free Have I Been Pwned "Pwned Passwords" service with its k-anonymity design: it hashes your password with SHA-1 on your own computer, sends only the **first five characters** of that hash, receives the few hundred hashes that start the same way, and looks for yours in that list locally. Neither your password nor your full hash ever leaves the machine, and the service can't tell which of the returned hashes you were checking.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python breach_password_checker.py                  # asks for the password; typing is hidden
echo 'my-password' | python breach_password_checker.py --stdin
python breach_password_checker.py --sha1 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8
python breach_password_checker.py --sha1 HASH --range-file saved-range.txt
```
There is deliberately no `--password` option: a password typed on the command line is saved in your shell history and visible to other programs. The prompt hides what you type, and `--stdin` suits scripts and password managers. The result says how many times the password appears in breaches and the exit code is 1 when it does. Requests ask for "padding" so the size of the answer doesn't reveal anything either. Only the prefix is ever printed, never the password or the hash.

## Example
```bash
python breach_password_checker.py --sha1 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8 --range-file hibp-range.txt
```
```
Checked hash prefix 5BAA6.... (6 candidate hashes returned)
FOUND: this password has appeared 9,545,824 times in data breaches. Don't use it.
```

## Notes
- The example hash is the SHA-1 of the word `password` and the range file is a saved, shortened response.
- "Not found" only means it isn't in the known breaches; short or predictable passwords are weak anyway.
- Never paste real passwords into websites that ask for them for "checking"; this tool is the safe way.
- The website demo can only use a saved range file; live checks work on your own computer.
