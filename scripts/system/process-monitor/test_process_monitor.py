import json

import process_monitor as pm
import pytest

PS = """  PID ELAPSED   TIME   RSS COMMAND
    1 1-00:00:00 00:01:10 12000 systemd
  812   86000 00:00:12   9800 /usr/sbin/sshd
 1051   85990 00:12:45  52000 nginx
 1052   85990 00:11:02  51000 nginx
 3301    7200 01:55:00 1850000 python
garbage line
"""

POWERSHELL = '''"Id","ProcessName","CPU","WorkingSet64"
"4","System","12.5","147456"
"900","chrome","340.25","209715200"
"901","chrome","","104857600"
"x","bad","1","2"
'''


@pytest.mark.parametrize("text,seconds", [("00:00:12", 12), ("03:04", 184), ("01:02:03", 3723),
                                          ("1-00:00:01", 86401), ("45", 45), ("00:00:01.50", 1.5)])
def test_parse_duration(text, seconds):
    assert pm.parse_duration(text) == seconds


def test_parse_ps_skips_headers_and_strips_paths():
    procs = pm.parse_ps(PS)
    assert [p["name"] for p in procs] == ["systemd", "sshd", "nginx", "nginx", "python"]
    assert procs[0]["age"] == 86400 and procs[1]["cpu_s"] == 12
    assert procs[4]["mem_mb"] == pytest.approx(1850000 / 1024)


def test_parse_powershell():
    procs = pm.parse_powershell(POWERSHELL)
    assert [p["pid"] for p in procs] == [4, 900, 901]
    assert procs[1]["cpu_s"] == 340.25 and procs[1]["mem_mb"] == 200 and procs[2]["cpu_s"] == 0


@pytest.mark.parametrize("name,patterns,expected", [
    ("nginx", [], True), ("nginx", ["ngi"], True), ("NGINX", ["nginx"], True),
    ("nginx", ["ng*x"], True), ("nginx", ["^nginx$"], False), ("python3", ["py*"], True),
    ("chrome", ["nginx", "chro"], True)])
def test_matches(name, patterns, expected):
    assert pm.matches(name, patterns) is expected


def test_group_computes_cpu_percent_from_two_samples():
    before = [{"pid": 1, "name": "a", "cpu_s": 10.0, "mem_mb": 5.0},
              {"pid": 2, "name": "a", "cpu_s": 4.0, "mem_mb": 5.0}]
    after = [{"pid": 1, "name": "a", "cpu_s": 11.0, "mem_mb": 6.0},
             {"pid": 2, "name": "a", "cpu_s": 4.5, "mem_mb": 7.0},
             {"pid": 3, "name": "a", "cpu_s": 99.0, "mem_mb": 1.0},  # new: no delta known
             {"pid": 4, "name": "other", "cpu_s": 1.0, "mem_mb": 1.0}]
    groups = pm.group(after, ["a"], before, 2.0)
    assert list(groups) == ["a"] and groups["a"]["count"] == 3
    assert groups["a"]["cpu_pct"] == pytest.approx(75.0)  # (1.0 + 0.5) / 2s
    assert groups["a"]["mem_mb"] == 14.0
    assert pm.group(after, [])["a"]["cpu_pct"] is None


def test_monitor_samples_with_an_injected_clock():
    readings = iter([[{"pid": 1, "name": "x", "cpu_s": 0.0, "mem_mb": 1.0}],
                     [{"pid": 1, "name": "x", "cpu_s": 1.0, "mem_mb": 1.0}],
                     [{"pid": 1, "name": "x", "cpu_s": 3.0, "mem_mb": 1.0}]])
    slept = []
    results = list(pm.monitor(lambda: next(readings), [], 2.0, 2, slept.append))
    assert slept == [2.0, 2.0]
    assert [r["x"]["cpu_pct"] for r in results] == [50.0, 100.0]


def test_alerts():
    groups = {"a": {"count": 1, "mem_mb": 900.0, "cpu_s": 0, "cpu_pct": 95.0},
              "b": {"count": 1, "mem_mb": 10.0, "cpu_s": 0, "cpu_pct": None}}
    assert pm.alerts(groups, 90, 500) == ["a: CPU 95% is over 90%",
                                          "a: memory 900 MB is over 500 MB"]
    assert pm.alerts(groups, None, None) == []
    assert pm.alerts({"b": groups["b"]}, 1, None) == []  # no CPU % in a snapshot


def test_cli_snapshot_from_file(tmp_path, capsys):
    saved = tmp_path / "ps.txt"
    saved.write_text(PS)
    assert pm.main(["--from-file", str(saved), "nginx", "python"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].split() == ["process", "count", "memory", "MB", "CPU", "time"]
    assert out.splitlines()[1].startswith("python") and "1:55:00" in out
    assert "nginx" in out and "sshd" not in out
    assert pm.main(["--from-file", str(saved), "--format", "csv", "nginx"]) == 0
    assert capsys.readouterr().out.splitlines()[1] == '"nginx",2,100.6,,1427.0'
    assert pm.main(["--from-file", str(saved), "--format", "json", "sshd"]) == 0
    assert json.loads(capsys.readouterr().out)["sshd"]["count"] == 1
    assert pm.main(["--from-file", str(saved), "--mem-over", "1000"]) == 1
    assert "ALERT python: memory 1807 MB is over 1000 MB" in capsys.readouterr().out


def test_cli_errors(tmp_path, capsys):
    saved = tmp_path / "ps.txt"
    saved.write_text(PS)
    assert pm.main(["--from-file", str(saved), "nothing-like-this"]) == 1
    assert "No matching processes" in capsys.readouterr().err
    assert pm.main(["--from-file", str(tmp_path / "none.txt")]) == 1
    for argv in (["--interval", "0"], ["--count", "0"], ["--top", "-1"]):
        with pytest.raises(SystemExit):
            pm.main(argv)


def test_live_listing_finds_this_python_process():
    names = {p["name"].lower() for p in pm.list_processes()}
    assert any("python" in name for name in names)
