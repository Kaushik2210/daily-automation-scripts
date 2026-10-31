import json

import system_info_report as sir


def test_gather_has_expected_keys():
    info = sir.gather()
    for key in ("hostname", "os", "cpu_count", "python", "disk_free_gb", "working_dir"):
        assert key in info
    assert info["python"].count(".") == 2


def test_memory_falls_back_to_none(monkeypatch):
    def broken(_name):
        raise ValueError("unsupported")
    monkeypatch.setattr(sir.os, "sysconf", broken, raising=False)
    assert sir.total_memory_bytes() is None


def test_json_output(capsys):
    assert sir.main(["--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["cpu_count"] >= 1


def test_table_output(capsys):
    sir.main([])
    out = capsys.readouterr().out
    assert "python" in out and "cpu count" in out
