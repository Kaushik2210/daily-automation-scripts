# password-strength-checker

## Purpose
Find out whether a password is any good and why. It estimates strength from length and character variety, and flags common passwords, repeated characters and easy sequences like `1234` or `qwer`. The password itself is never printed back.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python password_strength_checker.py [PASSWORD]
```
Without an argument it asks for the password with hidden input (or reads one line from a pipe). Typing a real password as an argument can leave it in your shell history, so prefer the prompt for anything you actually use. The exit code is 0 for strong passwords (3/4 or better) and 1 otherwise.

## Example
```bash
python password_strength_checker.py "summer2024"
```
```
Strength: very weak (0/4), about 33 bits
Length:   10 characters
- It is short (10 characters; aim for 12 or more).
- It mixes too few kinds of characters (use upper, lower, digits, symbols).
```

## Notes
- The bit estimate is a rough upper bound and ignores dictionary attacks, so treat it as a guide, not a guarantee.
- Longer passphrases beat short, complicated ones.
- Nothing is stored or sent anywhere; everything runs locally.
