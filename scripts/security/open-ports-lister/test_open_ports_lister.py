import open_ports_lister as opl
import pytest

SS = """State   Recv-Q  Send-Q   Local Address:Port    Peer Address:Port  Process
LISTEN  0       128            0.0.0.0:22           0.0.0.0:*      users:(("sshd",pid=812,fd=3))
LISTEN  0       4096         127.0.0.1:5432         0.0.0.0:*      users:(("postgres",pid=990,fd=5))
LISTEN  0       128               [::]:22              [::]:*      users:(("sshd",pid=812,fd=4))
LISTEN  0       5            0.0.0.0:3306           0.0.0.0:*      users:(("mysqld",pid=1200,fd=22))
UNCONN  0       0            0.0.0.0:68             0.0.0.0:*
"""
NETSTAT = """Active Connections

  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       1012
  TCP    127.0.0.1:8080         0.0.0.0:0              LISTENING       7764
  TCP    192.168.1.20:50412     52.96.0.1:443          ESTABLISHED     9900
  TCP    [::1]:5432             [::]:0                 LISTENING       5120
  UDP    0.0.0.0:5353           *:*                                    2210
"""
LSOF = """COMMAND   PID  USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
node     4120 sam   23u  IPv4 0xabc      0t0  TCP *:3000 (LISTEN)
postgres  801 sam    7u  IPv4 0xdef      0t0  TCP 127.0.0.1:5432 (LISTEN)
Chrome   9000 sam   40u  IPv4 0x123      0t0  TCP 10.0.0.5:51000->1.2.3.4:443 (ESTABLISHED)
"""


@pytest.mark.parametrize("text,host,port", [
    ("0.0.0.0:80", "0.0.0.0", 80), ("[::1]:5432", "::1", 5432), ("*:3000", "*", 3000),
    ("[::]:22", "::", 22), ("127.0.0.1:631", "127.0.0.1", 631), ("*:*", "*", None)])
def test_split_address(text, host, port):
    assert opl.split_address(text) == (host, port)


def test_parse_ss_reads_programs_and_skips_headers():
    entries = opl.parse_ss(SS)
    assert [(e["proto"], e["port"], e["process"], e["pid"]) for e in entries] == [
        ("tcp", 22, "sshd", 812), ("tcp", 5432, "postgres", 990), ("tcp", 22, "sshd", 812),
        ("tcp", 3306, "mysqld", 1200), ("udp", 68, "", None)]


def test_parse_windows_netstat_keeps_only_listeners():
    entries = opl.parse_windows_netstat(NETSTAT)
    assert [(e["proto"], e["address"], e["port"], e["pid"]) for e in entries] == [
        ("tcp", "0.0.0.0", 135, 1012), ("tcp", "127.0.0.1", 8080, 7764), ("tcp", "::1", 5432, 5120),
        ("udp", "0.0.0.0", 5353, 2210)]


def test_parse_lsof_listeners_only():
    entries = opl.parse_listing(LSOF)
    assert [(e["port"], e["process"], e["pid"]) for e in entries] == [(3000, "node", 4120),
                                                                      (5432, "postgres", 801)]


def test_parse_listing_detects_the_format():
    assert len(opl.parse_listing(SS)) == 5 and len(opl.parse_listing(NETSTAT)) == 4
    assert opl.parse_listing("nothing useful here") == []


def test_merge_combines_ipv4_and_ipv6_and_judges_exposure():
    rows = opl.merge(opl.parse_ss(SS))
    by_port = {(r["port"], r["proto"]): r for r in rows}
    ssh = by_port[(22, "tcp")]
    assert ssh["addresses"] == {"0.0.0.0", "::"} and ssh["exposed"] is True
    assert by_port[(5432, "tcp")]["exposed"] is False
    lan = opl.merge([{"proto": "tcp", "address": "192.168.1.20", "port": 139, "process": "",
                      "pid": 4}])
    assert lan[0]["exposed"] is True
    assert [r["port"] for r in rows] == sorted(r["port"] for r in rows)


def test_report_flags_risky_exposed_services(tmp_path, capsys):
    path = tmp_path / "ss.txt"
    path.write_text(SS)
    assert opl.main(["--parse", str(path)]) == 0
    out = capsys.readouterr().out
    assert "3306  tcp    all interfaces" in out and "<-- risky to expose" in out
    assert "5432  tcp    this computer" in out and out.count("<-- risky") == 1
    assert "4 listening port(s): 3 reachable from other computers, 1 local only." in out
    assert "sshd (pid 812)" in out


def test_only_exposed_hides_local_ports(tmp_path, capsys):
    path = tmp_path / "ss.txt"
    path.write_text(SS)
    assert opl.main(["--parse", str(path), "--only-exposed"]) == 0
    assert "postgres" not in capsys.readouterr().out


def test_collect_uses_the_platform_tool(monkeypatch):
    calls = []

    def fake_run(command):
        calls.append(command[0])
        if command[0] == "tasklist":
            return '"nginx.exe","1012","Console","1","10,000 K"\n'
        return NETSTAT if command[0] == "netstat" else SS

    monkeypatch.setattr(opl, "run", fake_run)
    monkeypatch.setattr(opl.sys, "platform", "win32")
    entries = opl.collect()
    assert calls == ["netstat", "tasklist"] and entries[0]["process"] == "nginx.exe"
    monkeypatch.setattr(opl.sys, "platform", "linux")
    assert opl.collect()[0]["process"] == "sshd"


def test_errors(tmp_path, capsys):
    empty = tmp_path / "empty.txt"
    empty.write_text("no ports in here")
    assert opl.main(["--parse", str(empty)]) == 1
    assert "No listening ports found in that file." in capsys.readouterr().out
    assert opl.main(["--parse", str(tmp_path / "gone.txt")]) == 1
