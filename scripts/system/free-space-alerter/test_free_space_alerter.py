from collections import namedtuple

import free_space_alerter as fsa
import pytest

Usage = namedtuple("Usage", "total used free")


def fake(total, free):
    return lambda path: Usage(total, total - free, free)


def test_parse_size():
    assert fsa.parse_size("10GB") == 10 * 1024**3
    assert fsa.parse_size("512") == 512
    with pytest.raises(ValueError):
        fsa.parse_size("ten gigs")


def test_low_by_size_and_percent(monkeypatch):
    monkeypatch.setattr(fsa.shutil, "disk_usage", fake(1000, 100))
    assert fsa.check_space(".", min_free_bytes=200)[0] is True
    assert fsa.check_space(".", min_free_bytes=50)[0] is False
    assert fsa.check_space(".", min_free_percent=20)[0] is True
    assert fsa.check_space(".", min_free_percent=5)[0] is False


def test_exit_code_and_log(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(fsa.shutil, "disk_usage", fake(100 * 1024**3, 5 * 1024**3))
    log = tmp_path / "space.log"
    assert fsa.main([str(tmp_path), "--min-free", "10GB", "--log", str(log)]) == 1
    assert "LOW" in capsys.readouterr().out
    assert "LOW" in log.read_text()
    assert fsa.main([str(tmp_path), "--min-free", "1GB"]) == 0
