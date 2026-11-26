import csv
import json
from datetime import UTC, datetime
from types import SimpleNamespace

import event_log_exporter as ele
import pytest


def stamp(hour):
    return int(datetime(2026, 11, 24, hour, 0, tzinfo=UTC).timestamp() * 1e6)


JOURNAL = "\n".join(json.dumps(row) for row in [
    {"__REALTIME_TIMESTAMP": str(stamp(8)), "PRIORITY": "3", "_SYSTEMD_UNIT": "redis.service",
     "MESSAGE": "Failed to start Redis"},
    {"__REALTIME_TIMESTAMP": str(stamp(9)), "PRIORITY": "4", "SYSLOG_IDENTIFIER": "kernel",
     "MESSAGE": "Disk   usage\nat 91 percent"},
    {"__REALTIME_TIMESTAMP": str(stamp(10)), "PRIORITY": "6", "_SYSTEMD_UNIT": "sshd.service",
     "MESSAGE": "Accepted publickey"},
    {"__REALTIME_TIMESTAMP": str(stamp(11)), "PRIORITY": "3", "_SYSTEMD_UNIT": "nginx.service",
     "MESSAGE": [104, 105]},
    {"__REALTIME_TIMESTAMP": "garbage", "MESSAGE": "bad row"}]) + "\nnot json\n"

WINDOWS = json.dumps([
    {"TimeCreated": "/Date(1763971200000)/", "LevelDisplayName": "Error",
     "ProviderName": "Disk", "Id": 7, "Message": "The device has a bad block."},
    {"TimeCreated": "2026-11-24T10:00:00Z", "LevelDisplayName": "Warning",
     "ProviderName": "Service Control Manager", "Id": 7000, "Message": None},
    {"TimeCreated": "2026-11-24T11:00:00+00:00", "LevelDisplayName": "Information",
     "ProviderName": "Winlogon", "Id": 1, "Message": "ok"},
    {"LevelDisplayName": "Error"}])

MAC = "\n".join(json.dumps(row) for row in [
    {"timestamp": "2026-11-24 12:00:00.123456+0000", "messageType": "Error",
     "processImagePath": "/usr/libexec/airportd", "eventMessage": "Association failed"},
    {"timestamp": "2026-11-24 12:05:00.000000+0000", "messageType": "Default",
     "processImagePath": "/usr/bin/sudo", "eventMessage": "ok"}])


def test_parse_journal():
    events = ele.parse_journal(JOURNAL)
    assert [(e["level"], e["source"]) for e in events] == [
        ("error", "redis.service"), ("warning", "kernel"), ("info", "sshd.service"),
        ("error", "nginx.service")]
    assert events[0]["time"] == "2026-11-24T08:00:00Z"
    assert events[1]["message"] == "Disk usage at 91 percent"  # whitespace tidied
    assert events[3]["message"] == "hi"


def test_parse_windows_handles_both_time_styles_and_missing_messages():
    events = ele.parse_windows(WINDOWS)
    assert [e["level"] for e in events] == ["error", "warning", "info"]
    assert events[0]["time"] == "2025-11-24T08:00:00Z" and events[0]["id"] == 7
    assert events[1]["message"] == "" and events[2]["time"] == "2026-11-24T11:00:00Z"
    assert ele.parse_windows("") == []
    assert len(ele.parse_windows(json.dumps({"TimeCreated": "2026-01-01T00:00:00Z"}))) == 1


def test_parse_mac():
    events = ele.parse_mac(MAC)
    assert [(e["level"], e["source"]) for e in events] == [("error", "airportd"), ("info", "sudo")]
    assert events[0]["time"] == "2026-11-24T12:00:00Z"


def test_format_detection():
    assert ele.parse_any(JOURNAL)[0]["source"] == "redis.service"
    assert ele.parse_any(WINDOWS)[0]["source"] == "Disk"
    assert ele.parse_any(MAC)[0]["source"] == "airportd"


def test_select_filters_and_sorts():
    events = ele.parse_journal(JOURNAL)
    assert [e["source"] for e in ele.select(events, "warning", None, None, None)] == [
        "redis.service", "kernel", "nginx.service"]
    assert len(ele.select(events, "info", None, None, None)) == 4
    assert [e["source"] for e in ele.select(events, "info", 1, None, None)] == [
        "sshd.service", "nginx.service"]  # within 1 hour of the newest event
    assert [e["source"] for e in ele.select(events, "info", None, "REDIS", None)] == [
        "redis.service"]
    assert [e["source"] for e in ele.select(events, "info", None, None, "ssh")] == [
        "sshd.service"]


def test_render_formats():
    events = ele.parse_journal(JOURNAL)[:2]
    rows = list(csv.DictReader(ele.render(events, "csv").splitlines()))
    assert rows[0]["source"] == "redis.service" and list(rows[0]) == ele.FIELDS
    assert json.loads(ele.render(events, "json"))[1]["level"] == "warning"
    assert [json.loads(x)["level"] for x in ele.render(events, "jsonl").splitlines()] == [
        "error", "warning"]
    first = ele.render(events, "text").splitlines()[0]
    assert first.endswith("redis.service: Failed to start Redis")


def test_read_system_builds_the_right_command():
    seen = {}

    def fake(command, **kwargs):
        seen["command"] = command
        return SimpleNamespace(returncode=0, stdout="out", stderr="")

    assert ele.read_system(6, 50, "warning", fake, "Linux") == "out"
    assert seen["command"][:4] == ["journalctl", "--since", "6 hours ago", "-p"]
    assert seen["command"][4] == "warning" and seen["command"][-1] == "50"
    ele.read_system(6, 50, "error", fake, "Windows")
    assert seen["command"][0] == "powershell" and "Level=1,2" in seen["command"][-1]
    assert "MaxEvents 50" in seen["command"][-1]
    ele.read_system(3, 50, "error", fake, "Darwin")
    assert seen["command"][:4] == ["log", "show", "--last", "3h"]

    def failing(command, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="Access denied")

    with pytest.raises(OSError, match="Access denied"):
        ele.read_system(1, 5, "error", failing, "Linux")

    def missing(command, **kwargs):
        raise FileNotFoundError

    with pytest.raises(OSError, match="not installed"):
        ele.read_system(1, 5, "error", missing, "Linux")


def test_cli_exports_and_never_overwrites(tmp_path, capsys):
    saved = tmp_path / "j.jsonl"
    saved.write_text(JOURNAL)
    out = tmp_path / "events.csv"
    assert ele.main(["--from-file", str(saved), "--output", str(out)]) == 0
    said = capsys.readouterr().out
    assert "3 event(s): 2 error, 1 warning" in said and "top sources" in said
    assert len(out.read_text(encoding="utf-8").splitlines()) == 4  # header + 3 events
    assert ele.main(["--from-file", str(saved), "--output", str(out)]) == 1
    assert ele.main(["--from-file", str(saved), "--output", str(out), "--force",
                     "--level", "error", "--format", "jsonl"]) == 0
    assert len(out.read_text(encoding="utf-8").splitlines()) == 2


def test_cli_stdout_and_errors(tmp_path, capsys):
    saved = tmp_path / "j.jsonl"
    saved.write_text(JOURNAL)
    assert ele.main(["--from-file", str(saved), "--format", "text", "--limit", "2"]) == 0
    out = capsys.readouterr().out
    assert "kernel: Disk usage" in out and "redis.service" not in out  # newest two only
    assert ele.main(["--from-file", str(saved), "--contains", "no such text"]) == 1
    assert "No warning-or-higher events matched" in capsys.readouterr().err
    assert ele.main(["--from-file", str(tmp_path / "none")]) == 1
    for argv in (["--limit", "0"], ["--hours", "0"]):
        with pytest.raises(SystemExit):
            ele.main(argv)
