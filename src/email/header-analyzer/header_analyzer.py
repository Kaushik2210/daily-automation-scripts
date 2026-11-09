"""Trace the route an email took, and check its SPF, DKIM and DMARC results, from its headers."""
import argparse
import email
import email.policy
import re
import sys
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

FROM_RE = re.compile(r"\bfrom\s+([^\s;]+)(?:\s+\(([^)]*)\))?", re.IGNORECASE)
BY_RE = re.compile(r"\bby\s+([^\s;]+)", re.IGNORECASE)
AUTH_RE = re.compile(r"\b(spf|dkim|dmarc)\s*=\s*(\w+)", re.IGNORECASE)
SLOW_HOP_SECONDS = 300


def parse_received(value):
    """Pull the sending host, receiving host and time out of one Received header."""
    text = " ".join(str(value).split())
    from_match, by_match = FROM_RE.search(text), BY_RE.search(text)
    when = None
    if ";" in text:
        try:
            when = parsedate_to_datetime(text.rsplit(";", 1)[1].strip())
        except (TypeError, ValueError):
            when = None
    return {"from": from_match.group(1) if from_match else "?",
            "detail": from_match.group(2) if from_match and from_match.group(2) else "",
            "by": by_match.group(1) if by_match else "?", "when": when}


def build_hops(msg):
    """Hops in the order the message travelled (Received headers are stored newest first)."""
    return [parse_received(v) for v in reversed(msg.get_all("Received") or [])]


def auth_results(msg):
    """Return {'spf': 'pass', 'dkim': ..., 'dmarc': ...} from the receiving server's verdicts."""
    results = {}
    for header in msg.get_all("Authentication-Results") or []:
        for method, outcome in AUTH_RE.findall(str(header)):
            results.setdefault(method.lower(), outcome.lower())
    spf = re.match(r"\s*(\w+)", str(msg["Received-SPF"] or ""))
    if spf and "spf" not in results:
        results["spf"] = spf.group(1).lower()
    return results


def domain_of(address):
    return parseaddr(str(address or ""))[1].rpartition("@")[2].lower()


def find_warnings(msg, hops, results):
    warnings = []
    for method in ("spf", "dkim", "dmarc"):
        outcome = results.get(method)
        if outcome and outcome not in ("pass", "none", "neutral"):
            warnings.append(f"{method.upper()} result is '{outcome}'")
    if not results:
        warnings.append("no SPF/DKIM/DMARC results were recorded in the headers")
    sender, bounce = domain_of(msg["From"]), domain_of(msg["Return-Path"])
    if sender and bounce and not (bounce == sender or bounce.endswith("." + sender)
                                  or sender.endswith("." + bounce)):
        warnings.append(f"Return-Path domain ({bounce}) differs from the From domain ({sender})")
    reply = domain_of(msg["Reply-To"])
    if reply and sender and reply != sender:
        warnings.append(f"Reply-To goes to a different domain ({reply})")
    for number, (before, after) in enumerate(zip(hops, hops[1:], strict=False), 2):
        if before["when"] and after["when"]:
            wait = (after["when"] - before["when"]).total_seconds()
            if wait > SLOW_HOP_SECONDS:
                warnings.append(f"hop {number} took {int(wait // 60)} minutes")
            elif wait < -60:
                warnings.append(f"hop {number} has a timestamp earlier than the hop before it")
    return warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description="Trace the hops in an email's headers.")
    parser.add_argument("source", type=Path, help="an .eml file, or a text file of headers")
    args = parser.parse_args(argv)
    try:
        msg = email.message_from_bytes(args.source.read_bytes(), policy=email.policy.default)
    except OSError as err:
        print(f"Couldn't read {args.source}: {err.strerror or err}", file=sys.stderr)
        return 1

    hops, results = build_hops(msg), auth_results(msg)
    for label in ("From", "To", "Subject", "Date", "Message-ID"):
        if msg[label]:
            print(f"{label + ':':<12}{msg[label]}")
    print(f"\nRoute ({len(hops)} hop(s), oldest first):")
    if not hops:
        print("  no Received headers found")
    for number, hop in enumerate(hops, 1):
        stamp = hop["when"].strftime("%Y-%m-%d %H:%M:%S %z") if hop["when"] else "time unknown"
        delay = ""
        if number > 1 and hop["when"] and hops[number - 2]["when"]:
            delay = f"  (+{int((hop['when'] - hops[number - 2]['when']).total_seconds())}s)"
        print(f"  {number}. {hop['from']} -> {hop['by']}   {stamp}{delay}")
    timed = [h["when"] for h in hops if h["when"]]
    if len(timed) > 1:
        print(f"  total transit: {int((max(timed) - min(timed)).total_seconds())} seconds")
    print("\nAuthentication:")
    for method in ("spf", "dkim", "dmarc"):
        print(f"  {method.upper():<6}{results.get(method, 'not reported')}")
    signature = str(msg["DKIM-Signature"] or "")
    signer = re.search(r"\bd=([^;\s]+)", signature)
    if signer:
        print(f"  signed by {signer.group(1)}")
    warnings = find_warnings(msg, hops, results)
    print("\n" + ("Warnings:" if warnings else "No warnings."))
    for warning in warnings:
        print(f"  ! {warning}")
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
