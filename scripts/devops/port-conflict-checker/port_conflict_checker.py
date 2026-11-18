"""Check whether ports are free before starting services, and spot duplicates in compose files."""
import argparse
import errno
import re
import socket  # web-ok: the live check is skipped with --static; compose parsing works anywhere
import sys
from pathlib import Path

PORT_LINE = re.compile(r"^\s*-\s*[\"']?([0-9.:\-/a-z\[\]]+)[\"']?\s*(?:#.*)?$", re.IGNORECASE)


def expand(spec):
    """'8000' or '8000-8002' -> [8000, ...]."""
    spec = spec.strip()
    low, _, high = spec.partition("-")
    if not low.isdigit() or (high and not high.isdigit()):
        raise ValueError(f"not a port or range: {spec!r}")
    ports = list(range(int(low), int(high or low) + 1))
    if not ports or ports[0] < 1 or ports[-1] > 65535 or len(ports) > 1000:
        raise ValueError(f"port out of range: {spec!r}")
    return ports


def parse_compose(text):
    """Return [(service, host ip or '', port, protocol)] for every published host port."""
    found, service, in_ports, indent = [], "?", False, 0
    for line in text.replace("\r\n", "\n").split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        spaces = len(line) - len(line.lstrip())
        head = re.match(r"^(\s*)([A-Za-z0-9_.-]+):\s*$", line)
        if head and spaces == 2:
            service, in_ports = head.group(2), False
            continue
        if re.match(r"^\s*ports:\s*$", line):
            in_ports, indent = True, spaces
            continue
        if in_ports and spaces <= indent and not line.lstrip().startswith("-"):
            in_ports = False
        match = PORT_LINE.match(line) if in_ports else None
        if not match:
            continue
        spec, _, proto = match.group(1).partition("/")
        parts = spec.split(":")
        if len(parts) == 1:
            continue  # container port only: Docker picks a random host port
        host_ip, host_ports = ("", parts[0]) if len(parts) == 2 else (parts[0], parts[1])
        try:
            found += [(service, host_ip, port, proto or "tcp") for port in expand(host_ports)]
        except ValueError:
            continue
    return found


def find_duplicates(wanted):
    """wanted: [(service, ip, port, proto)]. Return {(port, proto): [services]} for clashes."""
    clashes = {}
    for index, (service, ip, port, proto) in enumerate(wanted):
        for other, other_ip, other_port, other_proto in wanted[index + 1:]:
            if (port, proto) == (other_port, other_proto) and (
                    not ip or not other_ip or ip == other_ip):
                names = clashes.setdefault((port, proto), [])
                for name in (service, other):
                    if name not in names:
                        names.append(name)
    return clashes


def port_state(port, host="0.0.0.0"):
    """'free', 'in use' or 'no permission' after trying to bind the port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError as err:
            if err.errno in (errno.EADDRINUSE, getattr(errno, "WSAEADDRINUSE", -1), 10048):
                return "in use"
            if err.errno in (errno.EACCES, 10013):
                return "no permission"  # on Windows 10013 also means 'taken exclusively'
            return f"error ({err.strerror})"
    return "free"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check ports before starting services.")
    parser.add_argument("ports", nargs="*", help="ports or ranges, e.g. 8000 8080-8082")
    parser.add_argument("--compose", type=Path, action="append", default=[],
                        help="docker-compose file whose published ports should be checked")
    parser.add_argument("--host", default="0.0.0.0", help="address to test (0.0.0.0)")
    parser.add_argument("--static", action="store_true",
                        help="only look for duplicates, don't test the ports on this machine")
    args = parser.parse_args(argv)
    if not args.ports and not args.compose:
        parser.error("give ports to check, or --compose FILE")

    wanted = []
    for spec in args.ports:
        try:
            wanted += [("(command line)", "", port, "tcp") for port in expand(spec)]
        except ValueError as err:
            parser.error(str(err))
    for path in args.compose:
        if not path.is_file():
            parser.error(f"not a file: {path}")
        wanted += [(f"{path.name}:{service}", ip, port, proto) for service, ip, port, proto
                   in parse_compose(path.read_text(encoding="utf-8", errors="replace"))]
    if not wanted:
        print("No published ports found.", file=sys.stderr)
        return 1

    clashes = find_duplicates(wanted)
    problems = 0
    for key in sorted({(port, proto) for _, _, port, proto in wanted}):
        users = ", ".join(sorted({s for s, _, p, pr in wanted if (p, pr) == key}))
        status = []
        if key in clashes:
            status.append(f"DUPLICATE ({' and '.join(clashes[key])})")
        if not args.static and key[1] == "tcp":
            state = port_state(key[0], args.host)
            if state != "free":
                status.append(state.upper())
        problems += bool(status)
        print(f"  {key[0]:>5}/{key[1]:<3} {', '.join(status) if status else 'ok':<34} {users}")
    ports = len({(p, pr) for _, _, p, pr in wanted})
    print(f"\n{ports} port(s) checked: {problems} problem(s)."
          + (" Machine check skipped (--static)." if args.static else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
