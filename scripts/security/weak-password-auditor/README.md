# weak-password-auditor

## Purpose
Check your own list of passwords for the problems that actually get accounts taken over: passwords
that are very common, short, built from keyboard patterns or a word plus a year, **reused across
accounts**, or just small variations of one base word. Everything happens on your computer and no
full password is ever printed.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python weak_password_auditor.py passwords.csv
python weak_password_auditor.py passwords.csv --format json
python weak_password_auditor.py export.csv --password-column Pass --label-column Name
python weak_password_auditor.py passwords.txt              # one password per line
python weak_password_auditor.py passwords.csv --fail-on critical    # exit 1 if any are critical
```

The CSV needs a `password` column (change it with `--password-column`). The first other column is
used to name each account (change it with `--label-column`). Most browsers and password managers
can export a list in this format.

What it looks for:
- **Very common passwords** (a built-in list of widely used ones) and their common variations.
- **Length:** under 8 characters is critical; under 12 is weak.
- **Patterns:** keyboard and number runs, repeated characters, a word followed by a year, a season
  or month plus digits, and the site or account name inside the password.
- **Reuse:** the same password on more than one account is always rated critical, however strong it
  looks, because one breach exposes all of them.
- **Variations:** `Summer2024!` and `Summer2025!` count as one base word that was only tweaked.

Each entry gets a rating (`critical`, `weak`, `fair` or `strong`) and a 0-100 score, and the report
lists only the ones that need attention. The password column is shown masked, for example
`S********** (11 chars)`.

## Example
`passwords-demo.csv`

```
Audited 10 password(s). Nothing was sent anywhere, and no full password is shown below.

9 critical, 0 weak, 0 fair, 1 strong

[CRITICAL] blog.example.com  a****** (7 chars)  score 0
    is only 7 characters long; is a word followed by a year
[CRITICAL] forum.example.com  p********** (11 chars)  score 0
    is a very common password; is short (11 characters; 12 or more is better)
[CRITICAL] game.example.com  l****** (7 chars)  score 0
    is a very common password; is only 7 characters long
[CRITICAL] mail.example.com  S********** (11 chars)  score 0
    is a very common password; is short (11 characters; 12 or more is better); is a word followed by a year; is a season or month plus numbers; is one of several variations of the same base word; is used for more than one account
[CRITICAL] shop.example.com  S********** (11 chars)  score 0
    is a very common password; is short (11 characters; 12 or more is better); is a word followed by a year; is a season or month plus numbers; is one of several variations of the same base word; is used for more than one account
[CRITICAL] social.example.com  S********** (11 chars)  score 0
    is a very common password; is short (11 characters; 12 or more is better); is a word followed by a year; is a season or month plus numbers; is one of several variations of the same base word
[CRITICAL] work-vpn  q********* (10 chars)  score 0
    is a very common password; is short (10 characters; 12 or more is better); contains a keyboard or number sequence
[CRITICAL] cloud.example.com  k********** (16 chars)  score 60
    is used for more than one account
[CRITICAL] notes.example.com  k********** (16 chars)  score 60
    is used for more than one account

Reused passwords:
  2 accounts share one password: mail.example.com, shop.example.com
  2 accounts share one password: cloud.example.com, notes.example.com

What to do: change the critical ones first, give every account its own long
random password (a password manager helps), and turn on two-factor sign-in.
```

## Notes
- This is a quick offline check, not proof that a password is safe. A password that passes can still
  have appeared in a breach; the `breach-password-checker` tool checks that using k-anonymity.
- Delete the CSV export when you're done; it holds your passwords in plain text.
- Every password in the demo file is made up.
