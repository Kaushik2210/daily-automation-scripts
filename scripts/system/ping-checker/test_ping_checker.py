import csv
from datetime import datetime

import ping_checker as pc
import pytest

LINUX = """PING example.com (93.184.216.34) 56(84) bytes of data.
64 bytes from 93.184.216.34: icmp_seq=1 ttl=56 time=12.4 ms
64 bytes from 93.184.216.34: icmp_seq=2 ttl=56 time=11.9 ms
64 bytes from 93.184.216.34: icmp_seq=3 ttl=56 time=48.2 ms

--- example.com ping statistics ---
5 packets transmitted, 4 received, 20% packet loss, time 4006ms
rtt min/avg/max/mdev = 11.900/21.150/48.200/15.620 ms
"""

WINDOWS = """Pinging example.com [93.184.216.34] with 32 bytes of data:
Reply from 93.184.216.34: bytes=32 time=12ms TTL=56
Reply from 93.184.216.34: bytes=32 time<1ms TTL=56

Ping statistics for 93.184.216.34:
    Packets: Sent = 4, Received = 2, Lost = 2 (50% loss),
Approximate round trip times in milli-seconds:
    Minimum = 1ms, Maximum = 12ms, Average = 6ms
"""

MAC = """--- 8.8.8.8 ping statistics ---
3 packets transmitted, 3 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 10.1/11.2/12.3/0.9 ms
"""


def test_parse_linux_windows_and_mac():
    linux = pc.parse_ping(LINUX)
    assert (linux["sent"], linux["received"], linux["loss"]) == (5, 4, 20.0)
    assert (linux["min"], linux["avg"], linux["max"]) == (11.9, 21.15, 48.2)
    win = pc.parse_ping(WINDOWS)
    assert (win["sent"], win["received"], win["loss"]) == (4, 2, 50.0)
    assert (win["min"], win["max"], win["avg"]) == (1.0, 12.0, 6.0)
    mac = pc.parse_ping(MAC)
    assert mac["received"] == 3 and mac["loss"] == 0.0 and mac["avg"] == 11.2


def test_parse_falls_back_to_individual_replies_and_handles_garbage():
    partial = pc.parse_ping("reply time=10 ms\nreply time=20 ms\n")
    assert partial["received"] == 2 and partial["avg"] == 15.0 and partial["sent"] is None
    nothing = pc.parse_ping("Request timed out.\nRequest timed out.\n")
    assert nothing["received"] is None and not nothing["min"]


def test_describe():
    text = pc.describe(pc.parse_ping(LINUX))
    assert text == "4/5 replies, 20% loss, min 11.9 / avg 21.1 / max 48.2 ms"
    down = {"sent": 4, "received": 0, "loss": 100.0, "min": None, "avg": None, "max": None}
    assert pc.describe(down) == "no replies"


def test_log_rows_and_header(tmp_path):
    log = tmp_path / "ping.csv"
    info = pc.parse_ping(LINUX)
    pc.log_row(log, "example.com", info, datetime(2026, 1, 5, 9, 0, 0))
    pc.log_row(log, "example.com", info, datetime(2026, 1, 5, 9, 5, 0))
    rows = list(csv.reader(log.open(encoding="utf-8")))
    assert rows[0] == pc.LOG_HEADER and len(rows) == 3
    assert rows[1][:4] == ["2026-01-05 09:00:00", "example.com", "5", "4"]


def test_cli_parse_mode_and_log(tmp_path, capsys):
    f, log = tmp_path / "ping.txt", tmp_path / "log.csv"
    f.write_text(LINUX)
    assert pc.main(["--parse", str(f), "--log", str(log)]) == 0
    assert capsys.readouterr().out.startswith("example.com")
    assert log.exists()
    f.write_text("Request timed out.\n")
    assert pc.main(["--parse", str(f)]) == 1


def test_run_mode_uses_the_system_ping(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(pc, "run_ping", lambda host, count: calls.append((host, count)) or LINUX)
    assert pc.main(["example.com", "-c", "5"]) == 0
    assert calls == [("example.com", 5)]
    assert "4/5 replies" in capsys.readouterr().out


def test_bad_input_is_rejected(capsys):
    assert pc.main(["bad host;rm"]) == 2
    assert "not a valid host name" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        pc.main([])
    with pytest.raises(SystemExit):
        pc.main(["example.com", "-c", "0"])
