# file-encryptor

## Purpose
Encrypt files with a passphrase before you store or send them, and decrypt them again later. It
never overwrites an existing file, and only deletes an original when you ask for it with `--apply`,
after checking that the encrypted copy really opens.

## Install
```
pip install -r requirements.txt
```
It needs the `cryptography` package and Python 3.11+.

## Usage
```
python file_encryptor.py encrypt report.pdf photos.zip           # writes report.pdf.enc, photos.zip.enc
python file_encryptor.py decrypt report.pdf.enc                  # writes report.pdf
python file_encryptor.py encrypt secrets.txt --output-dir ~/safe
python file_encryptor.py encrypt secrets.txt --remove-original           # preview only
python file_encryptor.py encrypt secrets.txt --remove-original --apply   # verify, then delete the original
```

- The passphrase is asked for with a hidden prompt (twice when encrypting). For scripts use the
  `FILE_ENCRYPTOR_PASSPHRASE` environment variable or `--passphrase-file FILE`. It is deliberately
  not a command-line option, since those are visible to other users and saved in shell history.
- Encrypting `a.txt` makes `a.txt.enc`; decrypting `a.txt.enc` makes `a.txt` (a file without the
  `.enc` ending becomes `name.decrypted`). If the result already exists, the file is skipped and
  left alone.
- A wrong passphrase, or a file that was changed, writes nothing and reports an error.
- Files over `--max-mb` (200) are skipped, because each file is processed in memory.

## Example
`decrypt secret.txt.enc --passphrase-file demo-passphrase.txt`

```
decrypted  secret.txt.enc -> secret.txt

1 of 1 file(s) decrypted.
```

## Notes
- Encryption is AES-256-GCM with a key made from the passphrase by scrypt. Every file gets its own
  random salt and nonce, and a changed file is detected when you decrypt it.
- File names, sizes and modification times are not hidden.
- **There is no recovery.** Lose the passphrase and the data is gone. A weak passphrase can be
  guessed offline, so use a long one.
- The demo file uses the public passphrase in `demo-passphrase.txt`.
