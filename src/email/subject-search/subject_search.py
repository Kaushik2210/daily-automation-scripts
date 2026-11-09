"""Search message subjects across IMAP folders (or saved mbox files). Read-only."""
import argparse
import email
import email.policy
import imaplib  # web-ok: only used when you search a live mailbox; --mbox needs no network
import mailbox
import os
import re
import sys
from email.utils import parsedate_to_datetime
from pathlib import Path

HEADER_FIELDS = "FROM SUBJECT DATE"


def matches(subject, words):
    """True when every word appears in the subject (ignoring case)."""
    text = (subject or "").casefold()
    return all(word.casefold() in text for word in words)


def summary(msg):
    try:
        when = parsedate_to_datetime(str(msg["Date"])).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        when = "unknown date"
    return when, str(msg["From"] or "(unknown sender)"), str(msg["Subject"] or "(no subject)")


def search_mbox(path, words):
    found = []
    for msg in mailbox.mbox(str(path)):
        parsed = email.message_from_bytes(msg.as_bytes(), policy=email.policy.default)
        if matches(str(parsed["Subject"] or ""), words):
            found.append(summary(parsed))
    return found


def connect():
    host, user = os.environ.get("IMAP_HOST"), os.environ.get("IMAP_USER")
    password = os.environ.get("IMAP_PASSWORD")
    if not (host and user and password):
        raise ValueError("set the IMAP_HOST, IMAP_USER and IMAP_PASSWORD environment variables")
    conn = imaplib.IMAP4_SSL(host, int(os.environ.get("IMAP_PORT", "993")))
    conn.login(user, password)
    return conn


def list_folders(conn):
    """Names of every selectable folder on the account."""
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


def search_folder(conn, folder, words):
    status, _ = conn.select(f'"{folder}"', readonly=True)
    if status != "OK":
        return []
    criteria = []
    for word in words:
        clean = word.replace("\\", "").replace('"', "")
        criteria += ["SUBJECT", f'"{clean}"']
    if all(word.isascii() for word in words):
        _, data = conn.search(None, *criteria)
    else:
        _, data = conn.search("UTF-8", *[c.encode("utf-8") for c in criteria])
    found = []
    for number in (data[0].split() if data and data[0] else []):
        _, parts = conn.fetch(number, f"(BODY.PEEK[HEADER.FIELDS ({HEADER_FIELDS})])")
        for item in parts:
            if isinstance(item, tuple):
                found.append(summary(email.message_from_bytes(item[1],
                                                              policy=email.policy.default)))
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description="Search subjects across folders, read-only.")
    parser.add_argument("words", nargs="+", help="words that must all appear in the subject")
    parser.add_argument("--mbox", type=Path, action="append", help="search a saved mbox file")
    parser.add_argument("--folder", action="append",
                        help="IMAP folder to search; repeat for several (default: all folders)")
    parser.add_argument("--limit", type=int, default=50, help="most results to show (50)")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    results = {}
    try:
        if args.mbox:
            for path in args.mbox:
                if not path.is_file():
                    parser.error(f"not a file: {path}")
                results[path.name] = search_mbox(path, args.words)
        else:
            conn = connect()
            try:
                for folder in args.folder or list_folders(conn):
                    results[folder] = search_folder(conn, folder, args.words)
            finally:
                conn.logout()
    except (imaplib.IMAP4.error, OSError, ValueError) as err:
        print(f"Couldn't search the mailbox: {err}", file=sys.stderr)
        return 1

    total, shown = sum(len(v) for v in results.values()), 0
    print(f"{total} match(es) for {' '.join(args.words)!r} in {len(results)} place(s):")
    for place, found in results.items():
        if not found or shown >= args.limit:
            continue
        print(f"\n{place}")
        for when, sender, subject in sorted(found, reverse=True)[:args.limit - shown]:
            print(f"  {when}  {subject}  <- {sender}")
            shown += 1
    if total > shown:
        print(f"\n... {total - shown} more not shown (raise --limit).")
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
