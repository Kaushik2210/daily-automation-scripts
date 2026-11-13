import socket
import threading

import port_scanner as ps
import pytest


@pytest.fixture
def listeners():
    """Two listening sockets on 127.0.0.1; the second one sends a banner."""
    servers, ports = [], []
    for greeting in (None, b"SSH-2.0-DemoServer_1.0\r\n"):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(5)
        ports.append(server.getsockname()[1])
        servers.append(server)

        def accept(srv=server, hello=greeting):
            while True:
                try:
                    conn, _ = srv.accept()
                except OSError:
                    return
                if hello:
                    conn.sendall(hello)
                conn.close()

        threading.Thread(target=accept, daemon=True).start()
    yield ports
    for server in servers:
        server.close()


def closed_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.mark.parametrize("spec,expected", [
    ("22,80,443", [22, 80, 443]), ("20-23", [20, 21, 22, 23]), ("443, 22,22", [22, 443]),
    ("8000-8002,80", [80, 8000, 8001, 8002])])
def test_parse_ports(spec, expected):
    assert ps.parse_ports(spec) == expected


def test_parse_ports_common_and_errors():
    assert 22 in ps.parse_ports("common") and 3306 in ps.parse_ports("common")
    for bad in ("", "abc", "0", "70000", "30-20", "1-", "80;443"):
        with pytest.raises(ValueError):
            ps.parse_ports(bad)


def test_service_names():
    assert ps.service_name(22) == "ssh" and ps.service_name(5432) == "postgresql"
    assert ps.service_name(1) in ("tcpmux", "unknown")


def test_is_own_network():
    assert all(ps.is_own_network(a) for a in ("127.0.0.1", "10.1.2.3", "192.168.0.5", "::1",
                                              "169.254.1.1"))
    assert not any(ps.is_own_network(a) for a in ("8.8.8.8", "1.1.1.1", "2001:4860:4860::8888"))


def test_scan_finds_open_ports_only(listeners):
    open_port = listeners[0]
    found = ps.scan("127.0.0.1", [open_port, closed_port()], timeout=0.5, threads=4)
    assert found == [(open_port, "")]


def test_banner_grabbing(listeners):
    found = ps.scan("127.0.0.1", listeners, timeout=0.5, threads=2, banner=True)
    assert dict(found)[listeners[1]] == "SSH-2.0-DemoServer_1.0" and dict(found)[listeners[0]] == ""


def test_cli_scans_localhost(listeners, capsys):
    ports = ",".join(str(p) for p in listeners)
    assert ps.main(["127.0.0.1", "--ports", ports, "--banner"]) == 0
    out = capsys.readouterr().out
    assert "2 open." in out and "SSH-2.0-DemoServer_1.0" in out


def test_cli_reports_no_open_ports(capsys):
    assert ps.main(["localhost", "--ports", str(closed_port()), "--timeout", "0.2"]) == 0
    out = capsys.readouterr().out
    assert "0 open" in out and "No open ports found" in out


def test_public_addresses_are_refused_without_confirmation(monkeypatch, capsys):
    def no_network(*args, **kwargs):
        raise AssertionError("must not connect")

    monkeypatch.setattr(ps.socket, "create_connection", no_network)
    assert ps.main(["8.8.8.8", "--ports", "80"]) == 2
    out = capsys.readouterr().out
    assert "public address" in out and "--i-own-this" in out


def test_confirmed_public_scan_proceeds(monkeypatch, capsys):
    seen = []

    def fake_scan(address, ports, *args, **kwargs):
        seen.append((address, ports))
        return []

    monkeypatch.setattr(ps, "scan", fake_scan)
    assert ps.main(["8.8.8.8", "--ports", "80,443", "--i-own-this"]) == 0
    assert seen == [("8.8.8.8", [80, 443])]


def test_explain_mode_scans_nothing(monkeypatch, capsys):
    def no_network(*args, **kwargs):
        raise AssertionError("must not connect")

    monkeypatch.setattr(ps.socket, "create_connection", no_network)
    assert ps.main(["--ports", "22,6379,12345", "--explain"]) == 0
    out = capsys.readouterr().out
    assert "ssh" in out and "Redis is often left open" in out and "12345" in out


def test_argument_limits(capsys):
    for args in (["--ports", "abc"], ["--threads", "0"], ["--threads", "900"],
                 ["--timeout", "0"], ["--timeout", "60"]):
        with pytest.raises(SystemExit):
            ps.main(args)
    assert ps.main(["no-such-host.invalid", "--ports", "80"]) == 1
