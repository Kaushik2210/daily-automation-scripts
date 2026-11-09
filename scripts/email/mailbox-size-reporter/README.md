# mailbox-size-reporter

## Purpose
Find out which folder is eating your mail quota. The tool lists every folder with its message count and total size, biggest first, plus a grand total. It is read-only: folders are opened read-only and only message sizes are requested (no message content is downloaded).

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
export IMAP_HOST=imap.example.com IMAP_USER=you@example.com IMAP_PASSWORD='app-password'
python mailbox_size_reporter.py [--folder INBOX --folder Archive] [--sort size|count|name]
python mailbox_size_reporter.py --mbox inbox.mbox --mbox archive.mbox
```
Credentials come from environment variables and are never printed. Without `--folder` every selectable folder is included. With `--mbox` each file is treated as one folder.

## Example
```bash
python mailbox_size_reporter.py --mbox inbox.mbox
```
```
Folder      Messages        Size
inbox.mbox         7     26.3 KB
Total              7     26.3 KB
```

## Notes
- Sizes are what the server reports for each message, including attachments.
- Some providers count labels as folders, so the same message can appear in more than one row and the total can exceed your real usage.
- Very large mailboxes may take a little while, since the server has to report a size for every message.
- The website demo can only read the sample mailbox; connecting to a real account works on your own computer.
