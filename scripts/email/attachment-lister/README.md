# attachment-lister

## Purpose
Find out where your mailbox space went. The tool lists the messages that carry attachments, with each file's name, type and real (decoded) size, and totals them up. It only reads mail: the folder is opened read-only and messages are fetched with `BODY.PEEK`, so nothing is flagged as read, downloaded to disk or deleted.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
export IMAP_HOST=imap.example.com IMAP_USER=you@example.com IMAP_PASSWORD='app-password'
python attachment_lister.py [--folder INBOX] [--limit 50] [--min-kb 100]
python attachment_lister.py --mbox saved-mail.mbox
```
Credentials come from environment variables and are never printed. Use `--min-kb` to focus on the big files.

## Example
```bash
python attachment_lister.py --mbox inbox.mbox --min-kb 3
```
```
2026-10-12  Alice Chen <alice@acme.test>
    Re: Invoice September
    - report.xlsx  (5.9 KB, application/vnd.ms-excel)
    - photo.jpg  (8.8 KB, image/jpeg)

1 of 7 message(s) have attachments: 2 file(s), 14.7 KB in total.
```

## Notes
- To measure attachments the tool has to download whole messages, so the default is the newest 50. Raise `--limit` when you're on a fast connection.
- Sizes are the files' real sizes, not the larger encoded size inside the email.
- Inline images in HTML mail can show up as attachments too.
- The website demo can only read the sample mailbox; connecting to a real account works on your own computer.
