"""Check email addresses for valid syntax and (optionally) a working mail server (MX record)."""
import argparse
import json
import re
import sys
import urllib.error  # web-ok: the network is only used for MX lookups; --no-mx stays offline
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

DOH = "https://cloudflare-dns.com/dns-query"
LOCAL_CHARS = re.compile(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+")
LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")


def check_syntax(address):
    """Return None if the address looks valid, otherwise a short reason it doesn't."""
    if address.count("@") != 1:
        return "needs exactly one @" if "@" in address else "missing @"
    local, domain = address.split("@")
    if len(address) > 254:
        return "longer than 254 characters"
    if not local:
        return "nothing before the @"
    if len(local) > 64:
        return "name part is longer than 64 characters"
    if not local.isascii():
        return "non-ASCII characters in the name part"
    if not LOCAL_CHARS.fullmatch(local):
        return "unusual characters in the name part"
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return "dots in the wrong place in the name part"
    try:
        ascii_domain = domain.encode("idna").decode("ascii") if domain else ""
    except UnicodeError:
        return "domain has a part that is too long or can't be used"
    labels = ascii_domain.split(".")
    if len(labels) < 2 or not all(labels):
        return "domain needs a dot, like example.com"
    if len(ascii_domain) > 253 or not all(LABEL.fullmatch(label) for label in labels):
        return "domain has invalid characters, hyphens or lengths"
    if labels[-1].isdigit():
        return "domain can't end in a number"
    return None


def dns_query(domain, record_type, timeout=10):
    query = urlencode({"name": domain, "type": record_type})
    request = urllib.request.Request(f"{DOH}?{query}", headers={
        "Accept": "application/dns-json", "User-Agent": "daily-automation-scripts/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read(1024 * 1024).decode("utf-8"))


def lookup_mx(domain):
    """Return ('mx', [hosts]), ('a', []) when only an address record exists, or ('none', [])."""
    ascii_domain = domain.encode("idna").decode("ascii")
    answers = dns_query(ascii_domain, "MX").get("Answer", [])
    records = sorted((int(a["data"].split()[0]), a["data"].split()[1].rstrip(".")) for a in answers
                     if a.get("type") == 15 and len(a.get("data", "").split()) == 2)
    if records:  # a "null MX" (just ".") means the domain says it accepts no mail
        hosts = [host for _, host in records if host]
        return ("mx", hosts) if hosts else ("none", [])
    if any(a.get("type") == 1 for a in dns_query(ascii_domain, "A").get("Answer", [])):
        return "a", []
    return "none", []


def read_list(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate email addresses.")
    parser.add_argument("addresses", nargs="*", help="addresses to check")
    parser.add_argument("--file", type=Path, help="text file with one address per line")
    parser.add_argument("--no-mx", action="store_true", help="check syntax only, no DNS lookups")
    args = parser.parse_args(argv)

    try:
        addresses = args.addresses + (read_list(args.file) if args.file else [])
    except OSError as err:
        print(f"Couldn't read {args.file}: {err.strerror or err}", file=sys.stderr)
        return 1
    if not addresses:
        parser.error("give addresses or --file FILE")

    cache, bad = {}, 0
    for address in addresses:
        problem = check_syntax(address)
        if problem:
            print(f"BAD   {address}  ({problem})")
            bad += 1
            continue
        if args.no_mx:
            print(f"ok    {address}  (syntax only)")
            continue
        domain = address.rpartition("@")[2]
        try:
            if domain not in cache:
                cache[domain] = lookup_mx(domain)
            kind, hosts = cache[domain]
        except (urllib.error.URLError, OSError, ValueError, KeyError) as err:
            why = getattr(err, "reason", err)
            print(f"??    {address}  (couldn't check the mail server: {why})")
            bad += 1
            continue
        if kind == "mx":
            print(f"ok    {address}  (mail server: {hosts[0]})")
        elif kind == "a":
            print(f"warn  {address}  (no MX record, but the domain has an address record)")
        else:
            print(f"BAD   {address}  (domain has no mail server)")
            bad += 1
    print(f"{len(addresses) - bad} of {len(addresses)} address(es) look fine.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
