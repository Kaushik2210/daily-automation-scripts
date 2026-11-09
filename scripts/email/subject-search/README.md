# subject-search

## Purpose
Find that one email without a mail app. Give it a few words and it searches the subject lines of every folder on your account (or just the folders you name) and lists the matches with date, subject and sender. The search is done by the mail server and is read-only: folders are opened read-only and only headers are fetched with `BODY.PEEK`.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
export IMAP_HOST=imap.example.com IMAP_USER=you@example.com IMAP_PASSWORD='app-password'
python subject_search.py WORD [WORD ...] [--folder INBOX --folder Archive] [--limit 50]
python subject_search.py WORD --mbox saved-mail.mbox [--mbox other.mbox]
```
Every word has to appear in the subject, in any order and any case. Without `--folder` every selectable folder is searched. The exit code is 1 when nothing matched.

## Example
```bash
python subject_search.py invoice --mbox inbox.mbox
```
```
2 match(es) for 'invoice' in 1 place(s):

inbox.mbox
  2026-10-12  Re: Invoice September  <- Alice Chen <alice@acme.test>
  2026-09-15  Invoice September  <- Alice Chen <alice@acme.test>
```

## Notes
- Searches with non-English characters use the server's UTF-8 search; very old servers may not support it.
- Only subjects are searched, not message bodies.
- Credentials come from environment variables and are never printed.
- The website demo can only search the sample mailbox; connecting to a real account works on your own computer.
