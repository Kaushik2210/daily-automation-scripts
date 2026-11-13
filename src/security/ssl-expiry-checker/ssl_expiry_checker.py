"""Check when the TLS certificates of websites (or saved .pem files) expire."""
import argparse
import base64
import re
import socket  # web-ok: the network is only used for live domains; --pem files work anywhere
import ssl
import sys
from datetime import UTC, date, datetime
from pathlib import Path

NAMES = {"2.5.4.3": "CN", "2.5.4.6": "C", "2.5.4.7": "L", "2.5.4.8": "ST", "2.5.4.10": "O",
         "2.5.4.11": "OU"}
PEM_BLOCK = re.compile(r"-----BEGIN CERTIFICATE-----(.+?)-----END CERTIFICATE-----", re.DOTALL)


def read_tlv(data, offset=0):
    """Read one DER element. Returns (tag, value bytes, offset after the element)."""
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
    first = body[0]
    parts, value = [first // 40, first % 40], 0
    for byte in body[1:]:
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            parts.append(value)
            value = 0
    return ".".join(map(str, parts))


def decode_name(value):
    """A distinguished name as a list of (short name, text), e.g. [('CN', 'example.com')]."""
    pairs = []
    for _tag, rdn in children(value):
        for _t, attribute in children(rdn):
            oid, text = children(attribute)
            pairs.append((NAMES.get(decode_oid(oid[1]), decode_oid(oid[1])),
                          text[1].decode("utf-8", errors="replace")))
    return pairs


def decode_time(tag, body):
    text = body.decode("ascii")
    if tag == 0x17:  # UTCTime: YYMMDDHHMMSSZ, years 50-99 are 19xx
        year = int(text[:2])
        text = ("19" if year >= 50 else "20") + text
    return datetime.strptime(text[:14], "%Y%m%d%H%M%S").replace(tzinfo=UTC)


def dns_names(extension_value):
    names = []
    for tag, body in children(read_tlv(extension_value)[1]):
        if tag == 0x82:
            names.append(body.decode("ascii", errors="replace"))
    return names


def parse_certificate(der):
    """Pull the fields we need out of a DER certificate (no third-party libraries)."""
    _tag, certificate, _ = read_tlv(der)
    tbs = children(read_tlv(certificate)[1])
    items = [body for _tag, body in tbs]
    tags = [tag for tag, _ in tbs]
    index = 1 if tags[0] == 0xA0 else 0  # skip the optional explicit version
    serial = items[index]
    issuer, validity, subject = items[index + 2:index + 5]
    times = children(validity)
    cert = {"serial": serial.hex(), "issuer": decode_name(issuer), "subject": decode_name(subject),
            "not_before": decode_time(times[0][0], times[0][1]),
            "not_after": decode_time(times[1][0], times[1][1]), "san": [], "is_ca": False}
    for tag, body in tbs[index + 6:]:
        if tag != 0xA3:
            continue
        for _t, extension in children(children(body)[0][1]):
            parts = children(extension)
            oid, value = decode_oid(parts[0][1]), parts[-1][1]
            if oid == "2.5.29.17":
                cert["san"] = dns_names(value)
            elif oid == "2.5.29.19":
                flags = children(read_tlv(value)[1])
                cert["is_ca"] = bool(flags and flags[0][0] == 0x01 and flags[0][1] != b"\x00")
    return cert


def pem_to_der(text):
    return [base64.b64decode(block) for block in PEM_BLOCK.findall(text)]


def name_text(pairs, key="CN"):
    return next((value for k, value in pairs if k == key), "") or ", ".join(
        f"{k}={v}" for k, v in pairs)


def host_matches(host, names):
    host = host.lower()
    for name in names:
        name = name.lower()
        if name == host or (name.startswith("*.") and host.split(".", 1)[-1] == name[2:]
                            and "." in host):
            return True
    return False


def fetch_certificate(host, port, timeout=8):
    """Download a server's certificate without judging it, so expired ones can still be read."""
    context = ssl.create_default_context()
    context.check_hostname, context.verify_mode = False, ssl.CERT_NONE
    with (socket.create_connection((host, port), timeout=timeout) as raw,
          context.wrap_socket(raw, server_hostname=host) as tls):
        return tls.getpeercert(binary_form=True)


def judge(cert, host, today, warn_days):
    """Return (status label, days left)."""
    days = (cert["not_after"].date() - today).days
    if days < 0:
        return "EXPIRED", days
    if host and not host_matches(host, cert["san"] or [name_text(cert["subject"])]):
        return "NAME MISMATCH", days
    return ("EXPIRING SOON" if days <= warn_days else "OK"), days


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check TLS certificate expiry.")
    parser.add_argument("targets", nargs="+",
                        help="domains (example.com or example.com:8443) or .pem files")
    parser.add_argument("--warn-days", type=int, default=30, help="warn when this close (30)")
    parser.add_argument("--timeout", type=float, default=8, help="connection timeout (8 s)")
    parser.add_argument("--today", help="treat this date as today, YYYY-MM-DD (for testing)")
    args = parser.parse_args(argv)
    try:
        today = date.fromisoformat(args.today) if args.today else datetime.now(UTC).date()
    except ValueError:
        parser.error("--today must look like 2026-11-13")

    problems = 0
    for target in args.targets:
        host, label = "", target
        try:
            path = Path(target)
            if path.suffix.lower() in (".pem", ".crt", ".cer") and path.is_file():
                der = pem_to_der(path.read_text(encoding="utf-8", errors="replace"))[0]
            else:
                host, _, port = target.partition(":")
                der = fetch_certificate(host, int(port or 443), args.timeout)
                label = f"{host}:{port or 443}"
            cert = parse_certificate(der)
        except (OSError, ssl.SSLError, ValueError, IndexError, KeyError) as err:
            print(f"?  {label}: couldn't check ({err})")
            problems += 1
            continue
        status, days = judge(cert, host, today, args.warn_days)
        problems += status != "OK"
        when = f"{abs(days)} day(s) {'ago' if days < 0 else 'left'}"
        print(f"{status:<14} {label:<24} expires {cert['not_after']:%Y-%m-%d} ({when})")
        print(f"               subject {name_text(cert['subject'])}"
              f"; issuer {name_text(cert['issuer'])}")
        if cert["san"]:
            extra = f" (+{len(cert['san']) - 4} more)" if len(cert["san"]) > 4 else ""
            print(f"               names   {', '.join(cert['san'][:4])}{extra}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
