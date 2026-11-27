# password-vault

## Purpose
A minimal encrypted password store for the terminal: save logins, look them up, generate strong
random passwords, and see which entries haven't changed in a long time. Everything is in one file
that can't be read without your passphrase.

## Install
```
pip install -r requirements.txt
```
It needs the `cryptography` package and Python 3.11+.

## Usage
```
python password_vault.py add github --username ada --url https://github.com   # asks for the password
python password_vault.py add wifi --generate 24                                # makes a random one
python password_vault.py get github            # password is hidden
python password_vault.py get github --show     # reveal it
python password_vault.py get github --password-only | clip      # for piping, on Windows
python password_vault.py list --stale-days 180
python password_vault.py delete github --yes
python password_vault.py generate --length 20 --no-symbols     # no vault needed
```

- The default vault is `~/.password-vault.dat`; use `--vault FILE` for another. The first `add`
  creates it and asks for a new vault passphrase twice.
- The vault passphrase comes from a hidden prompt, the `PASSWORD_VAULT_PASSPHRASE` environment
  variable, or `--passphrase-file FILE`. Entry passwords come from a hidden prompt,
  `--password-file`, `--password-env` or `--generate`. None of them is a plain command-line option,
  because those are visible in process lists and shell history.
- Passwords are never printed unless you ask (`--show`, `--password-only`, or the one-time
  display after `--generate`).
- `add` won't overwrite an entry without `--replace`; `delete` needs `--yes`.

## Example
`get github --vault passwords.vault --passphrase-file demo-passphrase.txt`

```
Name:      github
Username:  ada
URL:       https://github.com
Password:  ********  (add --show)
Updated:   2026-11-02
```

## Notes
- Encryption is AES-256-GCM with a key derived from your passphrase by scrypt; the file is written
  through a temporary file and renamed, so a crash can't corrupt it.
- Entry names, usernames and URLs are encrypted too, not just passwords.
- **There is no recovery.** Forget the vault passphrase and the entries are gone, so keep a backup
  of the vault file and remember the passphrase.
- This is a small learning-sized tool. For critical accounts, a well-reviewed password manager is
  the safer choice.
