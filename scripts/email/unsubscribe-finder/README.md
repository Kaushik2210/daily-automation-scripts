# unsubscribe-finder

## Purpose
Clear out the newsletters you never read. The tool scans your recent mail for the standard `List-Unsubscribe` header that legitimate mailing lists include, groups the messages by sender, and shows how many each one sent along with the official unsubscribe links. It only reads headers (read-only, `BODY.PEEK`) and never unsubscribes for you, so you stay in control of what you click.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
export IMAP_HOST=imap.example.com IMAP_USER=you@example.com IMAP_PASSWORD='app-password'
python unsubscribe_finder.py [--folder INBOX] [--limit 200]
python unsubscribe_finder.py --mbox saved-mail.mbox
```
Credentials come from environment variables and are never printed. Senders are listed busiest first, with web links and `mailto:` addresses. A `[one-click supported]` note means the sender allows unsubscribing with a single request.

## Example
```bash
python unsubscribe_finder.py --mbox inbox.mbox
```
```
2 sender(s) offer an unsubscribe link (7 message(s) checked).

news@brief.example (Daily Brief) - 2 messages, latest: 'Your daily brief'
    web:  https://brief.example/unsub?u=1
    mail: unsubscribe@brief.example

deals@shop.example (Shop Deals) - 1 message, latest: '50% off this weekend'
    mail: stop@shop.example?subject=unsubscribe

Nothing was changed. Open a link yourself to unsubscribe.
```

## Notes
- Only the headers of the newest `--limit` messages are downloaded, so it stays fast on big mailboxes.
- Mail without a `List-Unsubscribe` header (including much spam) won't appear. Be wary of "unsubscribe" links in messages from senders you don't know.
- The website demo can only read the sample mailbox; connecting to a real account works on your own computer.
