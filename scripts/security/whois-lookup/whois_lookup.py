"""Look up who registered a domain, when it expires and which name servers it uses (WHOIS)."""
import argparse
import contextlib
import re
import socket  # web-ok: the network is only used for live lookups; --from-file works anywhere
import sys
from datetime import date, datetime
from pathlib import Path

IANA = "whois.iana.org"
PORT = 43
MAX_BYTES = 200_000
DOMAIN = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$",
                    re.IGNORECASE)
FIELDS = {
    "domain": ("domain name", "domain"),
    "registrar": ("registrar", "sponsoring registrar"),
    "created": ("creation date", "created", "registered on", "registration time"),
    "updated": ("updated date", "last updated", "last-update", "changed"),
    "expires": ("registry expiry date", "registrar registration expiration date", "expiry date",
                "expiration date", "expires on", "paid-till", "renewal date"),
    "dnssec": ("dnssec",),
    "organisation": ("registrant organization", "registrant organisation", "org"),
    "country": ("registrant country",),
    "abuse": ("registrar abuse contact email", "abuse contact email"),
}
LISTS = {"status": ("domain status", "status"), "name servers": ("name server", "nserver")}
DATE_FORMATS = ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
                "%d-%b-%Y", "%Y.%m.%d", "%d.%m.%Y", "%Y/%m/%d")


def ask(server, query, timeout=10):
    """One WHOIS exchange: send the query and read until the server closes the connection."""
    with socket.create_connection((server, PORT), timeout=timeout) as conn:
        conn.sendall(query.encode("ascii", errors="ignore") + b"\r\n")
        data = b""
        while len(data) < MAX_BYTES:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
    return data.decode("utf-8", errors="replace")


def lookup(domain, timeout=10, follow=True):
    """Ask IANA which registry runs the domain's top level, then ask that registry."""
    referral = re.search(r"^refer:\s*(\S+)", ask(IANA, domain.rsplit(".", 1)[-1], timeout),
                         re.MULTILINE | re.IGNORECASE)
    if not referral:
        raise ValueError("couldn't find a WHOIS server for that top-level domain")
    text = ask(referral.group(1), domain, timeout)
    deeper = re.search(r"^\s*Registrar WHOIS Server:\s*(\S+)", text, re.MULTILINE | re.IGNORECASE)
    if follow and deeper and deeper.group(1).lower() != referral.group(1).lower():
        with contextlib.suppress(OSError):  # the registry's own answer is still useful
            text = ask(deeper.group(1), domain, timeout) or text
    return text


def parse_whois(text):
    """Turn WHOIS text into a dict of single values and lists (names are normalised)."""
    values, lists = {}, {name: [] for name in LISTS}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        key, value = key.strip().lower(), value.strip()
        if not sep or not value or line.startswith((">>>", "%", "#")):
            continue
        for name, aliases in LISTS.items():
            item = value.split(" ")[0] if name == "status" else value.lower()
            if key in aliases and item not in lists[name]:
                lists[name].append(item)
        for name, aliases in FIELDS.items():
            if key in aliases and name not in values:
                values[name] = value
    return {**values, **{k: v for k, v in lists.items() if v}}


def parse_date(text):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip().split(" (")[0], fmt).date()
        except ValueError:
            continue
    return None


def describe_expiry(expires, today):
    when = parse_date(expires)
    if when is None:
        return expires
    days = (when - today).days
    state = f"{days} day(s) left" if days >= 0 else f"expired {-days} day(s) ago"
    return f"{when} ({state})"


def render(info, today):
    if not info:
        return ["No registration details were found (the domain may be unregistered, or "
                "its registry hides details)."]
    lines = []
    for label, key in (("Domain", "domain"), ("Registrar", "registrar"), ("Created", "created"),
                       ("Updated", "updated"), ("Expires", "expires"),
                       ("Organisation", "organisation"), ("Country", "country"),
                       ("DNSSEC", "dnssec"), ("Abuse contact", "abuse")):
        if key in info:
            value = info[key]
            if key in ("created", "updated"):
                value = str(parse_date(value) or value)
            elif key == "expires":
                value = describe_expiry(value, today)
            lines.append(f"{label + ':':<15}{value}")
    for label, key in (("Status", "status"), ("Name servers", "name servers")):
        for number, value in enumerate(info.get(key, [])):
            lines.append(f"{(label + ':') if number == 0 else '':<15}{value}")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="WHOIS lookup for a domain.")
    parser.add_argument("domain", nargs="?", help="the domain, e.g. example.com")
    parser.add_argument("--from-file", type=Path, help="read saved WHOIS text instead of asking")
    parser.add_argument("--raw", action="store_true", help="print the full WHOIS text as well")
    parser.add_argument("--no-follow", action="store_true",
                        help="don't ask the registrar's own server for extra detail")
    parser.add_argument("--timeout", type=float, default=10, help="seconds to wait (10)")
    parser.add_argument("--today", help="treat this date as today, YYYY-MM-DD (for testing)")
    args = parser.parse_args(argv)
    if not (args.domain or args.from_file):
        parser.error("give a domain or --from-file FILE")
    domain = (args.domain or "").strip().rstrip(".").lower()
    if args.domain and not DOMAIN.match(domain):
        parser.error(f"{args.domain!r} doesn't look like a domain name")
    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
    except ValueError:
        parser.error("--today must look like 2026-11-13")

    try:
        text = (args.from_file.read_text(encoding="utf-8", errors="replace") if args.from_file
                else lookup(domain, args.timeout, not args.no_follow))
    except (OSError, ValueError) as err:
        print(f"Couldn't complete the WHOIS lookup: {err}", file=sys.stderr)
        return 1
    info = parse_whois(text)
    print("\n".join(render(info, today)))
    if args.raw:
        print("\n----- raw WHOIS text -----\n" + text.rstrip())
    return 0 if info else 1


if __name__ == "__main__":
    sys.exit(main())
