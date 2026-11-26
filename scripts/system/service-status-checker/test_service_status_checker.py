import json
from types import SimpleNamespace

import pytest
import service_status_checker as ssc

SYSTEMCTL = """nginx.service loaded active running A high performance web server
redis-server.service loaded failed failed Advanced key-value store
docker.service loaded inactive dead Docker Application Container Engine
cron.service loaded active exited Regular background processing
not-a-service.socket loaded active listening Something
"""
SC = """SERVICE_NAME: Spooler
DISPLAY_NAME: Print Spooler
        STATE              : 4  RUNNING

SERVICE_NAME: W32Time
DISPLAY_NAME: Windows Time
        STATE              : 1  STOPPED

SERVICE_NAME: BITS
DISPLAY_NAME: Background Intelligent Transfer Service
        STATE              : 2  START_PENDING
"""
LAUNCHCTL = """PID\tStatus\tLabel
312\t0\tcom.apple.Finder
-\t0\tcom.example.idle
-\t78\tcom.example.broken
"""


def test_parse_systemctl_maps_states():
    services = ssc.parse_systemctl(SYSTEMCTL)
    assert [(s["name"], s["state"]) for s in services] == [
        ("nginx", "running"), ("redis-server", "failed"), ("docker", "stopped"),
        ("cron", "running")]
    assert services[0]["display"] == "A high performance web server"
    assert services[3]["detail"] == "active/exited"


def test_parse_sc_blocks():
    services = ssc.parse_sc(SC.replace("\n", "\r\n"))
    assert [(s["name"], s["state"]) for s in services] == [
        ("Spooler", "running"), ("W32Time", "stopped"), ("BITS", "start pending")]
    assert services[1]["display"] == "Windows Time"


def test_parse_launchctl():
    services = ssc.parse_launchctl(LAUNCHCTL)
    assert [(s["name"], s["state"]) for s in services] == [
        ("com.apple.Finder", "running"), ("com.example.idle", "stopped"),
        ("com.example.broken", "failed")]


def test_format_detection():
    assert ssc.detect_and_parse(SC)[0]["name"] == "Spooler"
    assert ssc.detect_and_parse(SYSTEMCTL)[0]["name"] == "nginx"
    assert ssc.detect_and_parse(LAUNCHCTL)[0]["name"] == "com.apple.Finder"
    assert ssc.detect_and_parse("nothing useful") == []


def test_find_prefers_exact_then_display_then_substring():
    services = ssc.parse_systemctl(SYSTEMCTL) + ssc.parse_sc(SC)
    assert ssc.find(services, "NGINX.service")["name"] == "nginx"
    assert ssc.find(services, "print spooler")["name"] == "Spooler"
    assert ssc.find(services, "redis")["name"] == "redis-server"
    assert ssc.find(services, "nope") is None


def test_check_flags_unexpected_states():
    services = ssc.parse_systemctl(SYSTEMCTL)
    results = ssc.check(services, ["nginx", "docker", "ghost"], "running")
    assert [r["ok"] for r in results] == [True, False, False]
    assert results[2]["state"] == "not found"
    assert [r["ok"] for r in ssc.check(services, ["docker"], "stopped")] == [True]


def test_collect_chooses_the_command_per_system():
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command[0])
        text = {"sc": SC, "launchctl": LAUNCHCTL}.get(command[0], SYSTEMCTL)
        return SimpleNamespace(returncode=0, stdout=text, stderr="")

    assert ssc.collect("Windows", fake_run)[0]["name"] == "Spooler"
    assert ssc.collect("Darwin", fake_run)[0]["name"] == "com.apple.Finder"
    assert ssc.collect("Linux", fake_run)[0]["name"] == "nginx"
    assert calls == ["sc", "launchctl", "systemctl"]

    def failing_run(command, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="Failed to connect to bus")

    with pytest.raises(OSError, match="Failed to connect"):
        ssc.collect("Linux", failing_run)


def test_cli(tmp_path, capsys):
    saved = tmp_path / "s.txt"
    saved.write_text(SYSTEMCTL)
    assert ssc.main(["--from-file", str(saved), "nginx", "cron"]) == 0
    out = capsys.readouterr().out
    assert "OK   nginx: running (active/running)" in out and "2 of 2 as expected" in out
    assert ssc.main(["--from-file", str(saved), "nginx", "docker", "ghost"]) == 1
    out = capsys.readouterr().out
    assert "FAIL docker: stopped" in out and "FAIL ghost: not found" in out
    assert ssc.main(["--from-file", str(saved), "docker", "--expect", "stopped"]) == 0
    capsys.readouterr()
    assert ssc.main(["--from-file", str(saved), "--list"]) == 0
    assert "redis-server  failed" in capsys.readouterr().out
    assert ssc.main(["--from-file", str(saved), "nginx", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["results"][0]["name"] == "nginx"


def test_cli_errors(tmp_path, capsys):
    assert ssc.main(["--from-file", str(tmp_path / "none.txt"), "x"]) == 1
    empty = tmp_path / "e.txt"
    empty.write_text("nothing here")
    assert ssc.main(["--from-file", str(empty), "x"]) == 1
    assert "No services were found" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        ssc.main(["--from-file", str(empty)])
