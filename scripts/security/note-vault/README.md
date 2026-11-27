# note-vault

## Purpose
Keep private notes in a single file that is encrypted with a passphrase. Nothing is readable
without the passphrase: not the notes, not even their titles.

## Install
```
pip install -r requirements.txt
```
It needs the `cryptography` package and Python 3.11+.

## Usage
```
python note_vault.py add "wifi router" --text "admin page is at 192.168.1.1"
python note_vault.py add "meeting" --file notes.txt
python note_vault.py list
python note_vault.py show "wifi router"
python note_vault.py search router
python note_vault.py delete "meeting"            # shows what it would delete
python note_vault.py delete "meeting" --yes
python note_vault.py list --vault ~/work.vault
```

- The vault is `~/.note-vault.dat` unless you pass `--vault`. The first `add` creates it and asks
  for a new passphrase twice.
- The passphrase is asked for with a hidden prompt. For scripts, put it in the
  `NOTE_VAULT_PASSPHRASE` environment variable, or use `--passphrase-file FILE` (first line). It is
  deliberately **not** a command-line option, because those show up in process lists and shell
  history.
- `add` never overwrites a note unless you add `--replace`, and `delete` needs `--yes`.
- Titles are matched without regard to case.

## Example
`list --vault demo.vault --passphrase-file demo-passphrase.txt`

```
api notes    updated 2026-11-12  (60 chars)
recipe       updated 2026-11-15  (56 chars)
wifi router  updated 2026-11-01  (66 chars)
```

## Notes
- Encryption is AES-256-GCM with a key made from your passphrase by scrypt (a deliberately slow
  function, to make guessing hard). Every save uses a new random salt and nonce, and the header is
  authenticated, so a changed file is detected instead of silently misread.
- The file is written through a temporary file and then renamed, so a crash can't leave a
  half-written vault.
- **There is no recovery.** If you forget the passphrase, the notes are gone. A weak passphrase can
  still be guessed offline, so use a long one.
- The demo vault uses the public passphrase in `demo-passphrase.txt`. Never use that for real notes.
