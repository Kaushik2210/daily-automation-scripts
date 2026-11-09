# email-digest

## Purpose
Get a quick summary of what's waiting in your inbox without opening a mail app. The tool lists your newest unread messages with sender, subject, size and a short preview. It is strictly read-only: the folder is opened in read-only mode and messages are fetched with `BODY.PEEK`, so nothing is marked as read, moved or deleted.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
export IMAP_HOST=imap.example.com IMAP_USER=you@example.com IMAP_PASSWORD='app-password'
python email_digest.py [--folder INBOX] [--limit 20] [--all] [--snippet 100]
python email_digest.py --mbox saved-mail.mbox
```
On Windows PowerShell set the variables with `$env:IMAP_HOST = "imap.example.com"` and so on. `IMAP_PORT` defaults to 993 (SSL). Use an app password where your provider offers one; the password is only read from the environment and is never printed or stored. `--mbox` reads a mail export instead of connecting.

## Example
```bash
python email_digest.py --mbox inbox.mbox --limit 3
```
```
5 unread message(s) in inbox.mbox, showing the newest 3:

2026-11-01 07:30  Daily Brief <news@brief.example>
    Your daily brief  (314 B)
    Top stories for today. Schools add coding lessons.

2026-10-20 12:00  Shop Deals <deals@shop.example>
    50% off this weekend  (411 B)
    Big sale! Everything must go.

2026-10-12 09:12  Alice Chen <alice@acme.test>
    Re: Invoice September  (20.6 KB)
    Sending the spreadsheet and a photo of the receipt as well.
```

## Notes
- Only the first 20 KB of each message is downloaded, which is plenty for headers and a preview.
- "Unread" comes from the server's `UNSEEN` flag (or the `Status` header in an mbox file).
- Some providers need IMAP switched on in their settings before they accept the connection.
- The website demo can only read the sample mailbox; connecting to a real account works on your own computer.
