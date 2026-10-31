from collections import namedtuple

import disk_usage_reporter as dur

Usage = namedtuple("Usage", "total used free")


def test_human_size():
    assert dur.human_size(512) == "512 B"
    assert dur.human_size(1536) == "1.5 KB"
    assert dur.human_size(5 * 1024**4) == "5.0 TB"


def test_bar():
    assert dur.bar(50, 10) == "#####-----"
    assert dur.bar(0, 4) == "----"
    assert dur.bar(100, 4) == "####"


def test_real_folder_reports(tmp_path, capsys):
    assert dur.main([str(tmp_path), "--warn", "101"]) == 0
    assert "%" in capsys.readouterr().out


def test_almost_full_exit_code(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(dur.shutil, "disk_usage", lambda p: Usage(100, 95, 5))
    assert dur.main([str(tmp_path)]) == 1
    assert "almost full" in capsys.readouterr().out
