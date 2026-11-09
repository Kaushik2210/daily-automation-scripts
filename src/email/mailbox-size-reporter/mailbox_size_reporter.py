"""Report how many messages and how much space each mail folder uses. Read-only."""
import argparse
import imaplib  # web-ok: only used when you read a live mailbox; --mbox needs no network
import mailbox
import os
import re
import sys
from pathlib import Path


def human_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def mbox_report(paths):
    rows = []
    for path in paths:
        box = mailbox.mbox(str(path))
        rows.append((path.name, len(box), sum(len(msg.as_bytes()) for msg in box)))
    return rows


def connect():
    host, user = os.environ.get("IMAP_HOST"), os.environ.get("IMAP_USER")
    password = os.environ.get("IMAP_PASSWORD")
    if not (host and user and password):
        raise ValueError("set the IMAP_HOST, IMAP_USER and IMAP_PASSWORD environment variables")
    conn = imaplib.IMAP4_SSL(host, int(os.environ.get("IMAP_PORT", "993")))
    conn.login(user, password)
    return conn


def list_folders(conn):
    _, lines = conn.list()
    names = []
    for line in lines or []:
        text = line.decode("utf-8", "replace") if isinstance(line, bytes) else str(line)
        if "\\Noselect" in text:
            continue
        text = text.strip()
        match = re.search(r'"([^"]*)"$', text) or re.search(r"(\S+)$", text)
        if match:
            names.append(match.group(1))
    return names


def folder_size(conn, folder):
    """Return (message count, total bytes) using a read-only select and a size-only fetch."""
    status, data = conn.select(f'"{folder}"', readonly=True)
    if status != "OK":
        raise ValueError(f"couldn't open folder {folder}")
    count = int(data[0]) if data and data[0] else 0
    if not count:
        return 0, 0
    _, parts = conn.fetch("1:*", "(RFC822.SIZE)")
    total = 0
    for item in parts:
        raw = item[0] if isinstance(item, tuple) else item
        match = re.search(rb"RFC822\.SIZE (\d+)", raw if isinstance(raw, bytes) else b"")
        total += int(match.group(1)) if match else 0
    return count, total


def imap_report(conn, folders):
    return [(name, *folder_size(conn, name)) for name in folders or list_folders(conn)]


def sorted_rows(rows, order):
    if order == "name":
        return sorted(rows, key=lambda r: r[0].casefold())
    index = 2 if order == "size" else 1
    return sorted(rows, key=lambda r: (-r[index], r[0].casefold()))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report message counts and size per folder.")
    parser.add_argument("--mbox", type=Path, action="append",
                        help="report on a saved mbox file; repeat for several")
    parser.add_argument("--folder", action="append", help="only this IMAP folder; repeat for more")
    parser.add_argument("--sort", choices=["size", "count", "name"], default="size")
    args = parser.parse_args(argv)

    try:
        if args.mbox:
            for path in args.mbox:
                if not path.is_file():
                    parser.error(f"not a file: {path}")
            rows = mbox_report(args.mbox)
        else:
            conn = connect()
            try:
                rows = imap_report(conn, args.folder)
            finally:
                conn.logout()
    except (imaplib.IMAP4.error, OSError, ValueError) as err:
        print(f"Couldn't read the mailbox: {err}", file=sys.stderr)
        return 1

    if not rows:
        print("No folders found.")
        return 1
    width = max(len(name) for name, _, _ in rows)
    print(f"{'Folder':<{width}}  {'Messages':>8}  {'Size':>10}")
    for name, count, size in sorted_rows(rows, args.sort):
        print(f"{name:<{width}}  {count:>8,}  {human_size(size):>10}")
    print(f"{'Total':<{width}}  {sum(r[1] for r in rows):>8,}  "
          f"{human_size(sum(r[2] for r in rows)):>10}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
