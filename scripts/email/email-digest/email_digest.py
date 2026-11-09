"""Summarize recent unread mail over IMAP (read-only) or from a saved mbox file."""
import argparse
import email
import email.policy
import imaplib  # web-ok: only used when you read a live mailbox; --mbox needs no network
import mailbox
import os
import re
import sys
from datetime import UTC
from email.utils import parsedate_to_datetime
from pathlib import Path

PARTIAL = 20000  # bytes of each message to download; enough for headers and the first text


def human_size(size):
    for unit in ("B", "KB", "MB"):
        if size < 1024 or unit == "MB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def message_date(msg):
    try:
        when = parsedate_to_datetime(str(msg["Date"]))
    except (TypeError, ValueError):
        return None
    return when.astimezone(UTC) if when.tzinfo else when.replace(tzinfo=UTC)


def snippet(msg, length):
    """First readable text of the message, whitespace squeezed to one line."""
    part, text = None, ""
    try:
        part = msg.get_body(preferencelist=("plain", "html"))
        text = part.get_content() if part else ""
    except (LookupError, ValueError, KeyError):
        text = ""
    if part is not None and part.get_content_subtype() == "html":
        text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())
    return text if len(text) <= length else text[:length - 3].rstrip() + "..."


def summarize(msg, size, length):
    when = message_date(msg)
    return {"date": when, "from": str(msg["From"] or "(unknown sender)"),
            "subject": str(msg["Subject"] or "(no subject)"), "size": size,
            "snippet": snippet(msg, length) if length else ""}


def from_mbox(path, include_read, length):
    box = mailbox.mbox(str(path))
    found = []
    for msg in box:
        status = (msg.get("Status") or "") + (msg.get("X-Status") or "")
        if "R" in status and not include_read:
            continue
        parsed = email.message_from_bytes(msg.as_bytes(), policy=email.policy.default)
        found.append(summarize(parsed, len(msg.as_bytes()), length))
    return found


def connect():
    host, user = os.environ.get("IMAP_HOST"), os.environ.get("IMAP_USER")
    password = os.environ.get("IMAP_PASSWORD")
    if not (host and user and password):
        raise ValueError("set the IMAP_HOST, IMAP_USER and IMAP_PASSWORD environment variables")
    conn = imaplib.IMAP4_SSL(host, int(os.environ.get("IMAP_PORT", "993")))
    conn.login(user, password)
    return conn


def from_imap(conn, folder, include_read, limit, length):
    """Fetch the newest messages without changing any flags (select is read-only)."""
    status, _ = conn.select(f'"{folder}"', readonly=True)
    if status != "OK":
        raise ValueError(f"couldn't open folder {folder}")
    _, data = conn.search(None, "ALL" if include_read else "UNSEEN")
    ids = data[0].split()[-limit:] if data and data[0] else []
    found = []
    for number in ids:
        _, parts = conn.fetch(number, f"(RFC822.SIZE BODY.PEEK[]<0.{PARTIAL}>)")
        for item in parts:
            if isinstance(item, tuple):
                size = re.search(rb"RFC822\.SIZE (\d+)", item[0])
                parsed = email.message_from_bytes(item[1], policy=email.policy.default)
                found.append(summarize(parsed, int(size.group(1)) if size else len(item[1]),
                                       length))
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarize unread mail, read-only.")
    parser.add_argument("--mbox", type=Path, help="read a saved mbox file instead of IMAP")
    parser.add_argument("--folder", default="INBOX", help="IMAP folder (INBOX)")
    parser.add_argument("--limit", type=int, default=20, help="newest messages to show (20)")
    parser.add_argument("--all", action="store_true", help="include messages you've read")
    parser.add_argument("--snippet", type=int, default=100,
                        help="characters of preview (100, 0 = none)")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    try:
        if args.mbox:
            if not args.mbox.is_file():
                parser.error(f"not a file: {args.mbox}")
            messages, where = from_mbox(args.mbox, args.all, args.snippet), str(args.mbox)
        else:
            conn = connect()
            try:
                messages = from_imap(conn, args.folder, args.all, args.limit, args.snippet)
            finally:
                conn.logout()
            where = args.folder
    except (imaplib.IMAP4.error, OSError, ValueError) as err:
        print(f"Couldn't read the mailbox: {err}", file=sys.stderr)
        return 1

    epoch = parsedate_to_datetime("Thu, 01 Jan 1970 00:00:00 +0000")
    messages.sort(key=lambda m: m["date"] or epoch, reverse=True)
    shown = messages[:args.limit]
    kind = "message(s)" if args.all else "unread message(s)"
    print(f"{len(messages)} {kind} in {where}" + (f", showing the newest {len(shown)}:"
                                                   if len(shown) < len(messages) else ":"))
    for item in shown:
        stamp = item["date"].strftime("%Y-%m-%d %H:%M") if item["date"] else "unknown date"
        print(f"\n{stamp}  {item['from']}\n    {item['subject']}  ({human_size(item['size'])})")
        if item["snippet"]:
            print(f"    {item['snippet']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
