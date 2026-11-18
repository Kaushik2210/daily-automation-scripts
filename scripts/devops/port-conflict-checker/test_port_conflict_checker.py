import socket

import port_conflict_checker as pcc
import pytest

COMPOSE = """services:
  web:
    image: app
    ports:
      - "8000:8000"
      - "8443:443"
  api:
    image: api
    ports:
      - 8000:3000
      - "127.0.0.1:9090:9090"
      - "7000"
  cache:
    ports:
      - "6380-6381:6380-6381"
      - 5353:5353/udp
    environment:
      - A=1
  other:
    ports:
      - "9090:9090"
"""


def test_expand():
    assert pcc.expand("80") == [80] and pcc.expand("8000-8002") == [8000, 8001, 8002]
    for bad in ("x", "0", "70000", "10-x", "1-5000"):
        with pytest.raises(ValueError):
            pcc.expand(bad)


def test_parse_compose():
    found = pcc.parse_compose(COMPOSE)
    assert ("web", "", 8000, "tcp") in found and ("web", "", 8443, "tcp") in found
    assert ("api", "", 8000, "tcp") in found and ("api", "127.0.0.1", 9090, "tcp") in found
    assert ("cache", "", 6380, "tcp") in found and ("cache", "", 6381, "tcp") in found
    assert ("cache", "", 5353, "udp") in found
    assert not any(port == 7000 for _, _, port, _ in found)  # container-only port
    assert not any(service == "?" for service, *_ in found)


def test_duplicates_consider_address_and_protocol():
    found = pcc.parse_compose(COMPOSE)
    clashes = pcc.find_duplicates(found)
    assert clashes == {(8000, "tcp"): ["web", "api"], (9090, "tcp"): ["api", "other"]}
    separate = [("a", "127.0.0.1", 80, "tcp"), ("b", "127.0.0.2", 80, "tcp"),
                ("c", "", 80, "udp")]
    assert pcc.find_duplicates(separate) == {}


def test_port_state_detects_a_listening_socket():
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        assert pcc.port_state(port, "127.0.0.1") in ("in use", "no permission")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free_port = probe.getsockname()[1]
    assert pcc.port_state(free_port, "127.0.0.1") == "free"


def test_cli_static_compose(tmp_path, capsys):
    path = tmp_path / "docker-compose.yml"
    path.write_text(COMPOSE)
    assert pcc.main(["--compose", str(path), "--static"]) == 1
    out = capsys.readouterr().out
    assert "8000/tcp DUPLICATE (docker-compose.yml:web and docker-compose.yml:api)" in out
    assert "9090/tcp DUPLICATE" in out and "8443/tcp ok" in out
    assert "5353/udp ok" in out and "2 problem(s)" in out and "--static" in out


def test_cli_live_check_of_ports_on_the_command_line(capsys):
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        assert pcc.main([str(port), "--host", "127.0.0.1"]) == 1
        out = capsys.readouterr().out
        assert "IN USE" in out or "NO PERMISSION" in out
    assert pcc.main([str(port), "--host", "127.0.0.1"]) == 0


def test_cli_errors(tmp_path):
    with pytest.raises(SystemExit):
        pcc.main([])
    with pytest.raises(SystemExit):
        pcc.main(["abc"])
    with pytest.raises(SystemExit):
        pcc.main(["--compose", str(tmp_path / "none.yml")])
    empty = tmp_path / "c.yml"
    empty.write_text("services: {}\n")
    assert pcc.main(["--compose", str(empty), "--static"]) == 1
