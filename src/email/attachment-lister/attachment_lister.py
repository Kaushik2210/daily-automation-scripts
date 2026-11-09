"""List the messages that have attachments, with file names and sizes. Read-only."""
import argparse
import email
import email.policy
import imaplib  # web-ok: only used when you read a live mailbox; --mbox needs no network
import mailbox
import os
import sys
from email.utils import parsedate_to_datetime
from pathlib import Path


def human_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def attachments_of(msg):
    """Return [(file name, content type, size in bytes)] for each attached file."""
    found = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        name = part.get_filename()
        if not name and part.get_content_disposition() != "attachment":
            continue
        payload = part.get_payload(decode=True) or b""
        found.append((str(name or "(unnamed)"), part.get_content_type(), len(payload)))
    return found


def describe(msg):
    try:
        when = parsedate_to_datetime(str(msg["Date"])).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        when = "unknown date"
    return when, str(msg["From"] or "(unknown sender)"), str(msg["Subject"] or "(no subject)")


def mbox_messages(path):
    for msg in mailbox.mbox(str(path)):
        yield email.message_from_bytes(msg.as_bytes(), policy=email.policy.default)


def connect():
    host, user = os.environ.get("IMAP_HOST"), os.environ.get("IMAP_USER")
    password = os.environ.get("IMAP_PASSWORD")
    if not (host and user and password):
        raise ValueError("set the IMAP_HOST, IMAP_USER and IMAP_PASSWORD environment variables")
    conn = imaplib.IMAP4_SSL(host, int(os.environ.get("IMAP_PORT", "993")))
    conn.login(user, password)
    return conn


def imap_messages(conn, folder, limit):
    status, _ = conn.select(f'"{folder}"', readonly=True)
    if status != "OK":
        raise ValueError(f"couldn't open folder {folder}")
    _, data = conn.search(None, "ALL")
    for number in (data[0].split()[-limit:] if data and data[0] else []):
        _, parts = conn.fetch(number, "(BODY.PEEK[])")
        for item in parts:
            if isinstance(item, tuple):
                yield email.message_from_bytes(item[1], policy=email.policy.default)


def main(argv=None):
    parser = argparse.ArgumentParser(description="List messages that have attachments.")
    parser.add_argument("--mbox", type=Path, help="read a saved mbox file instead of IMAP")
    parser.add_argument("--folder", default="INBOX", help="IMAP folder (INBOX)")
    parser.add_argument("--limit", type=int, default=50, help="newest messages to check (50)")
    parser.add_argument("--min-kb", type=float, default=0,
                        help="hide attachments smaller than this many KB")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    try:
        if args.mbox:
            if not args.mbox.is_file():
                parser.error(f"not a file: {args.mbox}")
            messages = list(mbox_messages(args.mbox))[-args.limit:]
        else:
            conn = connect()
            try:
                messages = list(imap_messages(conn, args.folder, args.limit))
            finally:
                conn.logout()
    except (imaplib.IMAP4.error, OSError, ValueError) as err:
        print(f"Couldn't read the mailbox: {err}", file=sys.stderr)
        return 1

    threshold = int(args.min_kb * 1024)
    with_files, total_files, total_bytes = 0, 0, 0
    for msg in messages:
        files = [a for a in attachments_of(msg) if a[2] >= threshold]
        if not files:
            continue
        with_files += 1
        when, sender, subject = describe(msg)
        print(f"\n{when}  {sender}\n    {subject}")
        for name, kind, size in files:
            print(f"    - {name}  ({human_size(size)}, {kind})")
            total_files, total_bytes = total_files + 1, total_bytes + size
    print(f"\n{with_files} of {len(messages)} message(s) have attachments: "
          f"{total_files} file(s), {human_size(total_bytes)} in total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
