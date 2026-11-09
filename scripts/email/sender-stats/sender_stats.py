"""Rank the senders (or domains) that fill your inbox, by message count and size. Read-only."""
import argparse
import email
import email.policy
import imaplib  # web-ok: only used when you read a live mailbox; --mbox needs no network
import mailbox
import os
import re
import sys
from email.utils import parseaddr
from pathlib import Path


def human_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def sender_key(from_header, by):
    address = parseaddr(str(from_header or ""))[1].lower() or "(unknown)"
    if by == "domain":
        return address.rpartition("@")[2] or address
    return address


def rank(items, by="address"):
    """items are (From header, size). Return [(sender, count, total size)], busiest first."""
    totals = {}
    for from_header, size in items:
        count, total = totals.get(sender_key(from_header, by), (0, 0))
        totals[sender_key(from_header, by)] = (count + 1, total + size)
    return sorted(((k, c, s) for k, (c, s) in totals.items()), key=lambda r: (-r[1], -r[2], r[0]))


def mbox_items(path):
    for msg in mailbox.mbox(str(path)):
        yield msg["From"], len(msg.as_bytes())


def connect():
    host, user = os.environ.get("IMAP_HOST"), os.environ.get("IMAP_USER")
    password = os.environ.get("IMAP_PASSWORD")
    if not (host and user and password):
        raise ValueError("set the IMAP_HOST, IMAP_USER and IMAP_PASSWORD environment variables")
    conn = imaplib.IMAP4_SSL(host, int(os.environ.get("IMAP_PORT", "993")))
    conn.login(user, password)
    return conn


def imap_items(conn, folder, limit):
    """Ask for only the From line and size of each message, in one read-only request."""
    status, _ = conn.select(f'"{folder}"', readonly=True)
    if status != "OK":
        raise ValueError(f"couldn't open folder {folder}")
    _, data = conn.search(None, "ALL")
    ids = data[0].split()[-limit:] if data and data[0] else []
    if not ids:
        return
    wanted = "(RFC822.SIZE BODY.PEEK[HEADER.FIELDS (FROM)])"
    _, parts = conn.fetch(b",".join(ids).decode(), wanted)
    for item in parts:
        if isinstance(item, tuple):
            size = re.search(rb"RFC822\.SIZE (\d+)", item[0])
            header = email.message_from_bytes(item[1], policy=email.policy.default)
            yield header["From"], int(size.group(1)) if size else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rank the senders filling your inbox.")
    parser.add_argument("--mbox", type=Path, help="read a saved mbox file instead of IMAP")
    parser.add_argument("--folder", default="INBOX", help="IMAP folder (INBOX)")
    parser.add_argument("--limit", type=int, default=1000, help="newest messages to count (1000)")
    parser.add_argument("--top", type=int, default=10, help="how many senders to list (10)")
    parser.add_argument("--by", choices=["address", "domain"], default="address",
                        help="group by full address or just the domain")
    args = parser.parse_args(argv)
    if args.limit < 1 or args.top < 1:
        parser.error("--limit and --top must be at least 1")

    try:
        if args.mbox:
            if not args.mbox.is_file():
                parser.error(f"not a file: {args.mbox}")
            items = list(mbox_items(args.mbox))[-args.limit:]
        else:
            conn = connect()
            try:
                items = list(imap_items(conn, args.folder, args.limit))
            finally:
                conn.logout()
    except (imaplib.IMAP4.error, OSError, ValueError) as err:
        print(f"Couldn't read the mailbox: {err}", file=sys.stderr)
        return 1

    if not items:
        print("No messages found.")
        return 0
    ranking = rank(items, args.by)
    print(f"{len(items)} message(s) from {len(ranking)} {args.by}(es):\n")
    width = max(len(name) for name, _, _ in ranking[:args.top])
    for name, count, size in ranking[:args.top]:
        print(f"{name:<{width}}  {count:>5}  {count / len(items):>6.1%}  {human_size(size):>9}")
    if len(ranking) > args.top:
        print(f"... and {len(ranking) - args.top} more.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
