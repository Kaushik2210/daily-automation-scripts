# mbox-splitter

## Purpose
Cut a huge mail export into manageable pieces. Many mail programs export a whole mailbox as one `.mbox` file. This tool sorts the messages by the month they were sent and writes one file per month (`2026-09.mbox`, `2026-10.mbox`, ...), which are easier to archive, search and import. The original file is only read, never changed.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python mbox_splitter.py all-mail.mbox [--out-dir pieces] [--prefix mail-] [--apply]
```
By default it only shows which files it would create and how many messages go in each. Add `--apply` to write them. Without `--out-dir` the pieces go next to the source file. A file that already exists is skipped, never overwritten.

## Example
```bash
python mbox_splitter.py inbox.mbox --out-dir pieces
```
```
2026-09.mbox: 2 message(s), 4.2 KB - would write
2026-10.mbox: 4 message(s), 21.8 KB - would write
2026-11.mbox: 1 message(s), 314 B - would write
7 message(s) would go into 3 file(s). Dry run - add --apply to write them.
```

## Notes
- The month comes from each message's `Date` header, or from the mbox `From ` line when the header is missing. Messages with no usable date go to `unknown-date.mbox`.
- Messages are copied as they are, including attachments.
- Keep the original export until you've checked the pieces.
- On the website demo the pieces are written to your browser's temporary folder.
