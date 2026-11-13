"""Look up DNS records (A, AAAA, MX, TXT, NS...) for a domain over DNS-over-HTTPS."""
import argparse
import json
import re
import sys
import urllib.error  # web-ok: the network is only used for live lookups; --from-file works anywhere
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

RESOLVERS = {"cloudflare": "https://cloudflare-dns.com/dns-query",
             "google": "https://dns.google/resolve"}
TYPES = {"A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "MX": 15, "TXT": 16, "AAAA": 28, "CAA": 257}
NUMBERS = {number: name for name, number in TYPES.items()}
STATUS = {0: "ok", 1: "the resolver couldn't parse the query", 2: "the DNS server failed",
          3: "the domain does not exist (NXDOMAIN)", 5: "the query was refused"}
DOMAIN = re.compile(r"^(?=.{1,253}$)([a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9_])?\.)+[a-z]{2,63}$",
                    re.IGNORECASE)


def query(domain, record_type, resolver="cloudflare", timeout=10):
    url = f"{RESOLVERS[resolver]}?{urlencode({'name': domain, 'type': record_type})}"
    request = urllib.request.Request(url, headers={
        "Accept": "application/dns-json", "User-Agent": "daily-automation-scripts/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read(1024 * 1024).decode("utf-8"))


def explain_txt(text):
    """Say what a TXT record is for, when it is one of the well-known kinds."""
    lowered = text.lower()
    for prefix, meaning in (("v=spf1", "SPF: which servers may send mail for this domain"),
                            ("v=dmarc1", "DMARC: what to do with mail that fails checks"),
                            ("v=dkim1", "DKIM: public key for signed mail"),
                            ("google-site-verification", "Google domain verification"),
                            ("ms=", "Microsoft 365 domain verification"),
                            ("facebook-domain-verification", "Facebook domain verification")):
        if lowered.startswith(prefix):
            return meaning
    return ""


def format_record(record_type, data):
    if record_type == "TXT":
        text = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', data)) or data
        note = explain_txt(text)
        return text + (f"   [{note}]" if note else "")
    if record_type == "MX":
        priority, _, host = data.partition(" ")
        return f"priority {priority:<3} {host.rstrip('.')}"
    return data.rstrip(".") if record_type in ("NS", "CNAME") else data


def render(domain, record_type, response):
    """Return the output lines for one record type."""
    status = response.get("Status", 0)
    if status != 0:
        return [f"{record_type:<6} {STATUS.get(status, f'DNS error {status}')}"]
    wanted = TYPES[record_type]
    answers = [a for a in response.get("Answer") or [] if a.get("type") == wanted]
    if not answers:
        cnames = [a for a in response.get("Answer") or [] if a.get("type") == 5]
        return [f"{record_type:<6} no {record_type} records" + (
            f" (it's an alias for {cnames[0]['data'].rstrip('.')})" if cnames else "")]
    lines = []
    for number, answer in enumerate(answers):
        label = record_type if number == 0 else ""
        text = format_record(record_type, answer["data"])
        lines.append(f"{label:<6} {text}  (TTL {answer['TTL']}s)")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="Look up DNS records for a domain.")
    parser.add_argument("domain", help="the domain, e.g. example.com")
    parser.add_argument("--types", default="A,AAAA,MX,TXT,NS",
                        help=f"record types, comma separated ({', '.join(TYPES)})")
    parser.add_argument("--resolver", choices=list(RESOLVERS), default="cloudflare",
                        help="which public DNS-over-HTTPS service to ask")
    parser.add_argument("--from-file", type=Path,
                        help="read saved answers ({type: response}) instead of asking")
    parser.add_argument("--timeout", type=float, default=10, help="seconds to wait (10)")
    args = parser.parse_args(argv)
    domain = args.domain.strip().rstrip(".").lower()
    if not DOMAIN.match(domain):
        parser.error(f"{args.domain!r} doesn't look like a domain name")
    types = [t.strip().upper() for t in args.types.split(",") if t.strip()]
    unknown = [t for t in types if t not in TYPES]
    if unknown or not types:
        parser.error(f"unknown record type(s): {', '.join(unknown) or '(none)'}; "
                     f"choose from {', '.join(TYPES)}")

    saved = None
    if args.from_file:
        try:
            saved = json.loads(args.from_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as err:
            print(f"Couldn't read {args.from_file}: {err}", file=sys.stderr)
            return 1
    print(f"DNS records for {domain}\n")
    failed = 0
    for record_type in types:
        try:
            response = (saved.get(record_type, {"Status": 0}) if saved is not None
                        else query(domain, record_type, args.resolver, args.timeout))
        except (urllib.error.URLError, OSError, ValueError) as err:
            print(f"{record_type:<6} lookup failed ({getattr(err, 'reason', err)})")
            failed += 1
            continue
        print("\n".join(render(domain, record_type, response)))
        failed += response.get("Status", 0) != 0
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
