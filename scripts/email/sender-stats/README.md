# sender-stats

## Purpose
See who is really filling your inbox. The tool counts the messages from each sender (or each domain) and ranks them by volume, with their share of your mail and the space they take. It is read-only: it opens the folder in read-only mode and asks the server for just the `From` line and size of each message, so it is quick even on big mailboxes.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
export IMAP_HOST=imap.example.com IMAP_USER=you@example.com IMAP_PASSWORD='app-password'
python sender_stats.py [--folder INBOX] [--limit 1000] [--top 10] [--by address|domain]
python sender_stats.py --mbox saved-mail.mbox
```
Credentials come from environment variables and are never printed. `--by domain` merges everything from one company, which is handy for spotting noisy services.

## Example
```bash
python sender_stats.py --mbox inbox.mbox --by domain
```
```
7 message(s) from 4 domain(es):

brief.example      3   42.9%     1.1 KB
acme.test          2   28.6%    24.5 KB
shop.example       1   14.3%      411 B
home.test          1   14.3%      313 B
```

## Notes
- Sizes are the full size of each message including attachments.
- Addresses are compared in lower case, so `Ann@Acme.test` and `ann@acme.test` count together.
- Only the newest `--limit` messages are counted.
- The website demo can only read the sample mailbox; connecting to a real account works on your own computer.
