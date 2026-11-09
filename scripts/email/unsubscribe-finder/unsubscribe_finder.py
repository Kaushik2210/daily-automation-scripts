"""Find newsletters and mailing lists that offer a List-Unsubscribe header. Read-only."""
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

HEADER_FIELDS = "FROM SUBJECT DATE LIST-UNSUBSCRIBE LIST-UNSUBSCRIBE-POST"


def parse_links(value):
    """Split a List-Unsubscribe header into (web links, mail addresses)."""
    web, mail = [], []
    for item in re.findall(r"<([^>]+)>", str(value or "")):
        item = item.strip()
        if item.lower().startswith(("http://", "https://")):
            web.append(item)
        elif item.lower().startswith("mailto:"):
            mail.append(item[7:])
    return web, mail


def find_lists(messages):
    """Group messages that carry List-Unsubscribe by sender address."""
    found = {}
    for msg in messages:
        web, mail = parse_links(msg["List-Unsubscribe"])
        if not (web or mail):
            continue
        name, address = parseaddr(str(msg["From"] or ""))
        entry = found.setdefault((address or "unknown").lower(), {
            "name": name, "count": 0, "subject": "", "web": [], "mail": [], "one_click": False})
        entry["count"] += 1
        entry["subject"] = str(msg["Subject"] or "")
        entry["one_click"] |= "one-click" in str(msg["List-Unsubscribe-Post"] or "").lower()
        entry["web"] += [link for link in web if link not in entry["web"]]
        entry["mail"] += [link for link in mail if link not in entry["mail"]]
    return found


def mbox_headers(path):
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


def imap_headers(conn, folder, limit):
    """Yield only the headers we need, using read-only select and BODY.PEEK."""
    status, _ = conn.select(f'"{folder}"', readonly=True)
    if status != "OK":
        raise ValueError(f"couldn't open folder {folder}")
    _, data = conn.search(None, "ALL")
    for number in (data[0].split()[-limit:] if data and data[0] else []):
        _, parts = conn.fetch(number, f"(BODY.PEEK[HEADER.FIELDS ({HEADER_FIELDS})])")
        for item in parts:
            if isinstance(item, tuple):
                yield email.message_from_bytes(item[1], policy=email.policy.default)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find mail that offers an unsubscribe link.")
    parser.add_argument("--mbox", type=Path, help="read a saved mbox file instead of IMAP")
    parser.add_argument("--folder", default="INBOX", help="IMAP folder (INBOX)")
    parser.add_argument("--limit", type=int, default=200, help="newest messages to check (200)")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    checked = 0
    try:
        if args.mbox:
            if not args.mbox.is_file():
                parser.error(f"not a file: {args.mbox}")
            source = list(mbox_headers(args.mbox))[-args.limit:]
        else:
            conn = connect()
            try:
                source = list(imap_headers(conn, args.folder, args.limit))
            finally:
                conn.logout()
        checked = len(source)
    except (imaplib.IMAP4.error, OSError, ValueError) as err:
        print(f"Couldn't read the mailbox: {err}", file=sys.stderr)
        return 1

    lists = find_lists(source)
    print(f"{len(lists)} sender(s) offer an unsubscribe link ({checked} message(s) checked).")
    for address, entry in sorted(lists.items(), key=lambda kv: -kv[1]["count"]):
        label = f" ({entry['name']})" if entry["name"] else ""
        plural = "s" if entry["count"] != 1 else ""
        print(f"\n{address}{label} - {entry['count']} message{plural}, "
              f"latest: {entry['subject']!r}")
        for link in entry["web"]:
            print(f"    web:  {link}" + ("   [one-click supported]" if entry["one_click"] else ""))
        for link in entry["mail"]:
            print(f"    mail: {link}")
    print("\nNothing was changed. Open a link yourself to unsubscribe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
