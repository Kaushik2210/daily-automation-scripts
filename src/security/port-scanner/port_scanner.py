"""Scan TCP ports on localhost or hosts you own; public addresses need explicit confirmation."""
import argparse
import ipaddress
import socket  # web-ok: scanning needs a real network; --explain works anywhere
import sys
import time
from concurrent.futures import ThreadPoolExecutor

SERVICES = {
    20: "ftp-data", 21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns", 67: "dhcp",
    80: "http", 110: "pop3", 111: "rpcbind", 123: "ntp", 135: "msrpc", 137: "netbios-ns",
    139: "netbios-ssn", 143: "imap", 161: "snmp", 389: "ldap", 443: "https", 445: "smb",
    465: "smtps", 514: "syslog", 587: "submission", 631: "ipp", 636: "ldaps", 873: "rsync",
    993: "imaps", 995: "pop3s", 1080: "socks", 1433: "mssql", 1521: "oracle", 2049: "nfs",
    2375: "docker (unencrypted)", 3000: "dev server", 3306: "mysql", 3389: "rdp",
    5000: "dev server", 5432: "postgresql", 5672: "amqp", 5900: "vnc", 6379: "redis",
    8000: "dev server", 8080: "http-alt", 8443: "https-alt", 9000: "dev server",
    9200: "elasticsearch", 11211: "memcached", 27017: "mongodb",
}
RISKY = {23: "telnet sends passwords in clear text", 2375: "Docker API without TLS",
         6379: "Redis is often left open without a password", 11211: "memcached has no login",
         27017: "check that MongoDB requires authentication", 5900: "VNC is weakly protected",
         3389: "RDP is a common attack target", 445: "SMB should not face the internet",
         21: "FTP sends passwords in clear text"}
COMMON = sorted(SERVICES)


def service_name(port):
    if port in SERVICES:
        return SERVICES[port]
    try:
        return socket.getservbyport(port, "tcp")
    except OSError:
        return "unknown"


def parse_ports(spec):
    """'22,80,443', '1-1024', 'common' or a mix such as '22,8000-8100' -> sorted unique list."""
    ports = set()
    for part in spec.split(","):
        part = part.strip().lower()
        if part == "common":
            ports.update(COMMON)
        elif "-" in part:
            low, _, high = part.partition("-")
            if not (low.isdigit() and high.isdigit()) or int(low) > int(high):
                raise ValueError(f"bad port range: {part!r}")
            ports.update(range(int(low), int(high) + 1))
        elif part.isdigit():
            ports.add(int(part))
        else:
            raise ValueError(f"bad port: {part!r}")
    if not ports or min(ports) < 1 or max(ports) > 65535:
        raise ValueError("ports must be between 1 and 65535")
    return sorted(ports)


def addresses_of(host):
    """Every IP address a host name resolves to (a literal IP resolves to itself)."""
    infos = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    return sorted({info[4][0].split("%")[0] for info in infos})


def is_own_network(address):
    ip = ipaddress.ip_address(address)
    return ip.is_loopback or ip.is_private or ip.is_link_local


def scan_port(address, port, timeout, banner=False):
    """Return (port, banner text) if the port accepts a connection, else None."""
    try:
        with socket.create_connection((address, port), timeout=timeout) as conn:
            text = ""
            if banner:
                conn.settimeout(min(timeout * 2, 1.5))
                try:
                    text = conn.recv(80).decode("utf-8", errors="replace").strip().splitlines()[0]
                except (OSError, IndexError):
                    text = ""
            return port, text
    except OSError:
        return None


def scan(address, ports, timeout=0.5, threads=100, banner=False):
    with ThreadPoolExecutor(max_workers=threads) as pool:
        found = [r for r in pool.map(lambda p: scan_port(address, p, timeout, banner), ports) if r]
    return sorted(found)


def main(argv=None):
    parser = argparse.ArgumentParser(description="TCP connect scan for hosts you own.")
    parser.add_argument("host", nargs="?", default="127.0.0.1", help="host to scan (127.0.0.1)")
    parser.add_argument("--ports", default="common",
                        help="22,80,443 or 1-1024 or common (default: a list of well-known ports)")
    parser.add_argument("--timeout", type=float, default=0.5, help="seconds to wait per port (0.5)")
    parser.add_argument("--threads", type=int, default=100, help="parallel connections (100)")
    parser.add_argument("--banner", action="store_true", help="show the first line a service sends")
    parser.add_argument("--i-own-this", action="store_true",
                        help="confirm you own the host or have written permission, to scan a "
                             "public address")
    parser.add_argument("--explain", action="store_true",
                        help="only describe what the ports are for; scan nothing")
    args = parser.parse_args(argv)
    try:
        ports = parse_ports(args.ports)
    except ValueError as err:
        parser.error(str(err))
    if not 1 <= args.threads <= 500:
        parser.error("--threads must be between 1 and 500")
    if not 0.05 <= args.timeout <= 10:
        parser.error("--timeout must be between 0.05 and 10 seconds")

    if args.explain:
        for port in ports[:200]:
            note = f"   ! {RISKY[port]}" if port in RISKY else ""
            print(f"{port:>5}  {service_name(port)}{note}")
        return 0

    try:
        addresses = addresses_of(args.host)
    except OSError as err:
        print(f"Couldn't resolve {args.host}: {err}", file=sys.stderr)
        return 1
    outside = [a for a in addresses if not is_own_network(a)]
    if outside and not args.i_own_this:
        print(f"{args.host} ({', '.join(outside)}) is a public address. Scanning machines you "
              "don't own can be illegal.\nIf it is yours, or you have written permission, repeat "
              "the command with --i-own-this.")
        return 2
    address = addresses[0]
    started = time.monotonic()
    found = scan(address, ports, args.timeout, args.threads, args.banner)
    took = time.monotonic() - started
    print(f"Scanned {len(ports):,} port(s) on {args.host} ({address}) in {took:.1f}s: "
          f"{len(found)} open.")
    for port, text in found:
        note = f"   ! {RISKY[port]}" if port in RISKY else ""
        print(f"  {port:>5}/tcp  open  {service_name(port)}" + (f"   [{text}]" if text else "")
              + note)
    if not found:
        print("  No open ports found (filtered ports and slow hosts may need a longer --timeout).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
