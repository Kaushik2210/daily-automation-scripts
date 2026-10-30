import os
import time

from old_file_finder import DAY, find_old_files, main


def touch_days_ago(path, days):
    path.write_text("x")
    stamp = time.time() - days * DAY
    os.utime(path, (stamp, stamp))


def test_only_old_files_returned(tmp_path):
    touch_days_ago(tmp_path / "old.txt", 400)
    touch_days_ago(tmp_path / "new.txt", 1)
    found = find_old_files(tmp_path, 30)
    assert [path.name for _, path in found] == ["old.txt"]


def test_oldest_first_and_nested(tmp_path):
    (tmp_path / "sub").mkdir()
    touch_days_ago(tmp_path / "a.txt", 100)
    touch_days_ago(tmp_path / "sub" / "b.txt", 200)
    names = [path.name for _, path in find_old_files(tmp_path, 30)]
    assert names == ["b.txt", "a.txt"]


def test_cli_summary(tmp_path, capsys):
    touch_days_ago(tmp_path / "old.txt", 50)
    main([str(tmp_path), "--days", "10"])
    assert "1 file(s) older than 10 days." in capsys.readouterr().out
