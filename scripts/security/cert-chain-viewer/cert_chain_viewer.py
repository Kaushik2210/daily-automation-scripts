"""Print a site's (or a .pem file's) TLS certificate chain: who issued each certificate and when."""
import argparse
import base64
import hashlib
import re
import socket  # web-ok: the network is only used for live hosts; .pem files work anywhere
import sys
import urllib.error
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path

NAMES = {"2.5.4.3": "CN", "2.5.4.6": "C", "2.5.4.7": "L", "2.5.4.8": "ST", "2.5.4.10": "O",
         "2.5.4.11": "OU"}
SIGNATURES = {
    "1.2.840.113549.1.1.5": "sha1WithRSA (weak)", "1.2.840.113549.1.1.11": "sha256WithRSA",
    "1.2.840.113549.1.1.12": "sha384WithRSA", "1.2.840.113549.1.1.13": "sha512WithRSA",
    "1.2.840.10045.4.3.2": "ecdsa-with-SHA256", "1.2.840.10045.4.3.3": "ecdsa-with-SHA384",
    "1.2.840.10045.4.3.4": "ecdsa-with-SHA512", "1.3.101.112": "Ed25519"}
CURVES = {"1.2.840.10045.3.1.7": "P-256", "1.3.132.0.34": "P-384", "1.3.132.0.35": "P-521"}
PEM_BLOCK = re.compile(r"-----BEGIN CERTIFICATE-----(.+?)-----END CERTIFICATE-----", re.DOTALL)
MAX_DEPTH = 6


def read_tlv(data, offset=0):
    tag, length = data[offset], data[offset + 1]
    offset += 2
    if length & 0x80:
        count = length & 0x7F
        length = int.from_bytes(data[offset:offset + count], "big")
        offset += count
    return tag, data[offset:offset + length], offset + length


def children(value):
    items, offset = [], 0
    while offset < len(value):
        tag, body, offset = read_tlv(value, offset)
        items.append((tag, body))
    return items


def decode_oid(body):
    parts, value = [body[0] // 40, body[0] % 40], 0
    for byte in body[1:]:
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            parts.append(value)
            value = 0
    return ".".join(map(str, parts))


def decode_name(value):
    pairs = []
    for _tag, rdn in children(value):
        for _t, attribute in children(rdn):
            oid, text = children(attribute)
            pairs.append((NAMES.get(decode_oid(oid[1]), decode_oid(oid[1])),
                          text[1].decode("utf-8", errors="replace")))
    return pairs


def decode_time(tag, body):
    text = body.decode("ascii")
    if tag == 0x17:
        text = ("19" if int(text[:2]) >= 50 else "20") + text
    return datetime.strptime(text[:14], "%Y%m%d%H%M%S").replace(tzinfo=UTC)


def describe_key(spki):
    algorithm, bits = children(spki)
    parts = children(algorithm[1])
    oid = decode_oid(parts[0][1])
    key = bits[1][1:]  # drop the "unused bits" byte
    if oid == "1.2.840.113549.1.1.1":
        modulus = children(read_tlv(key)[1])[0][1]
        return f"RSA {int.from_bytes(modulus, 'big').bit_length()}-bit"
    if oid == "1.2.840.10045.2.1":
        return f"EC {CURVES.get(decode_oid(parts[1][1]), 'unknown curve')}"
    if oid == "1.3.101.112":
        return "Ed25519"
    return f"key type {oid}"


def parse_certificate(der):
    """Decode the parts of a certificate people want to see (no signature checking)."""
    certificate = children(read_tlv(der)[1])
    tbs = children(certificate[0][1])
    items = [body for _tag, body in tbs]
    index = 1 if tbs[0][0] == 0xA0 else 0
    times = children(items[index + 3])
    cert = {"der": der, "serial": items[index].hex(),
            "signature": SIGNATURES.get(decode_oid(children(certificate[1][1])[0][1]),
                                        "other algorithm"),
            "issuer": decode_name(items[index + 2]), "subject": decode_name(items[index + 4]),
            "not_before": decode_time(*times[0]), "not_after": decode_time(*times[1]),
            "key": describe_key(items[index + 5]), "san": [], "is_ca": False, "ca_issuers": []}
    for tag, body in tbs[index + 6:]:
        if tag != 0xA3:
            continue
        for _t, extension in children(children(body)[0][1]):
            parts = children(extension)
            oid, value = decode_oid(parts[0][1]), parts[-1][1]
            if oid == "2.5.29.17":
                cert["san"] = [b.decode("ascii", errors="replace")
                               for t, b in children(read_tlv(value)[1]) if t == 0x82]
            elif oid == "2.5.29.19":
                flags = children(read_tlv(value)[1])
                cert["is_ca"] = bool(flags and flags[0][0] == 0x01 and flags[0][1] != b"\x00")
            elif oid == "1.3.6.1.5.5.7.1.1":  # Authority Information Access
                for _x, access in children(read_tlv(value)[1]):
                    method, location = children(access)
                    if decode_oid(method[1]) == "1.3.6.1.5.5.7.48.2" and location[0] == 0x86:
                        cert["ca_issuers"].append(location[1].decode("ascii", errors="replace"))
    return cert


def name_text(pairs):
    common = next((v for k, v in pairs if k == "CN"), "")
    org = next((v for k, v in pairs if k == "O"), "")
    return common or org or ", ".join(f"{k}={v}" for k, v in pairs) or "(empty)"


def fingerprint(der):
    digest = hashlib.sha256(der).hexdigest().upper()
    return ":".join(digest[i:i + 2] for i in range(0, 64, 2))


def pem_to_der(text):
    return [base64.b64decode(block) for block in PEM_BLOCK.findall(text)]


def der_from_download(data):
    """AIA downloads are DER or PEM; return DER bytes (or None if it is neither)."""
    if b"BEGIN CERTIFICATE" in data[:100]:
        found = pem_to_der(data.decode("ascii", errors="replace"))
        return found[0] if found else None
    return data if data[:1] == b"\x30" else None


def fetch_chain(host, port, timeout=8):
    """The certificates the server presents: the full chain on Python 3.13+, else leaf + AIA."""
    import ssl  # imported here because browsers running Python have no ssl module

    context = ssl.create_default_context()
    context.check_hostname, context.verify_mode = False, ssl.CERT_NONE
    with (socket.create_connection((host, port), timeout=timeout) as raw,
          context.wrap_socket(raw, server_hostname=host) as tls):
        if hasattr(tls, "get_unverified_chain"):
            chain = [c if isinstance(c, bytes) else c.public_bytes() for c in
                     tls.get_unverified_chain()]
            if chain:
                return chain, "as sent by the server"
        chain = [tls.getpeercert(binary_form=True)]
    for _ in range(MAX_DEPTH):  # older Python: follow "CA Issuers" links to find the parents
        cert = parse_certificate(chain[-1])
        if cert["issuer"] == cert["subject"] or not cert["ca_issuers"]:
            break
        try:
            request = urllib.request.Request(cert["ca_issuers"][0],
                                             headers={"User-Agent": "daily-automation-scripts/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                parent = der_from_download(response.read(200_000))
        except (urllib.error.URLError, OSError):
            break
        if not parent:
            break
        chain.append(parent)
    return chain, "leaf plus issuers found through its AIA links"


def check_links(certs):
    """Return a note for each step: does each certificate's issuer match the next subject?"""
    notes = []
    for number, cert in enumerate(certs[:-1]):
        ok = cert["issuer"] == certs[number + 1]["subject"]
        notes.append("issued by the next certificate" if ok
                     else "ISSUER DOES NOT MATCH the next certificate's subject")
    last = certs[-1]
    notes.append("self-signed root (the end of the chain)" if last["issuer"] == last["subject"]
                 else "not self-signed: the chain doesn't include its root (normal for servers; "
                      "browsers have the root)")
    return notes


def render(certs, today):
    lines, notes = [], check_links(certs)
    for number, (cert, note) in enumerate(zip(certs, notes, strict=True), 1):
        role = ("root CA" if cert["issuer"] == cert["subject"]
                else "intermediate CA" if cert["is_ca"] else "server certificate")
        days = (cert["not_after"].date() - today).days
        state = f"{days} day(s) left" if days >= 0 else f"EXPIRED {-days} day(s) ago"
        lines += [f"[{number}] {name_text(cert['subject'])}  ({role})",
                  f"    issuer     {name_text(cert['issuer'])}",
                  f"    valid      {cert['not_before']:%Y-%m-%d} to {cert['not_after']:%Y-%m-%d}"
                  f" ({state})",
                  f"    key        {cert['key']}, signed with {cert['signature']}",
                  f"    serial     {cert['serial'].upper()}",
                  f"    SHA-256    {fingerprint(cert['der'])}"]
        if cert["san"]:
            extra = f" (+{len(cert['san']) - 5} more)" if len(cert["san"]) > 5 else ""
            lines.append(f"    names      {', '.join(cert['san'][:5])}{extra}")
        lines.append(f"    link       {note}")
        lines.append("")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="Show a TLS certificate chain.")
    parser.add_argument("target", help="host (example.com or example.com:8443) or a .pem file")
    parser.add_argument("--timeout", type=float, default=8, help="seconds to wait (8)")
    parser.add_argument("--today", help="treat this date as today, YYYY-MM-DD (for testing)")
    args = parser.parse_args(argv)
    try:
        today = date.fromisoformat(args.today) if args.today else datetime.now(UTC).date()
    except ValueError:
        parser.error("--today must look like 2026-11-13")

    try:
        path = Path(args.target)
        if path.suffix.lower() in (".pem", ".crt", ".cer") and path.is_file():
            ders, source = pem_to_der(path.read_text(encoding="utf-8", errors="replace")), (
                f"from {path.name}")
        else:
            host, _, port = args.target.partition(":")
            ders, source = fetch_chain(host, int(port or 443), args.timeout)
        certs = [parse_certificate(der) for der in ders]
    except (OSError, ValueError, IndexError, KeyError) as err:
        print(f"Couldn't read the certificate chain: {err}", file=sys.stderr)
        return 1
    if not certs:
        print("No certificates found.", file=sys.stderr)
        return 1
    print(f"{len(certs)} certificate(s), {source}. Signatures are not verified here.\n")
    print("\n".join(render(certs, today)).rstrip())
    broken = any("DOES NOT MATCH" in note for note in check_links(certs))
    expired = any(c["not_after"].date() < today for c in certs)
    return 1 if broken or expired else 0


if __name__ == "__main__":
    sys.exit(main())
