import os
import time

from temp_cleaner import DAY, human_size, is_protected, main, old_files


def make(path, days_old):
    path.write_text("data")
    stamp = time.time() - days_old * DAY
    os.utime(path, (stamp, stamp))


def test_only_old_files_found(tmp_path):
    make(tmp_path / "old.tmp", 30)
    make(tmp_path / "new.tmp", 1)
    found = old_files(tmp_path, 7)
    assert [p.name for p, _ in found] == ["old.tmp"]


def test_protected_paths(tmp_path):
    assert is_protected(tmp_path.anchor and type(tmp_path)(tmp_path.anchor))
    assert is_protected(type(tmp_path).home())
    assert not is_protected(tmp_path)


def test_dry_run_then_apply(tmp_path, capsys):
    make(tmp_path / "old.tmp", 30)
    make(tmp_path / "new.tmp", 1)
    main([str(tmp_path)])
    assert (tmp_path / "old.tmp").exists()
    assert "Would delete 1 file(s)" in capsys.readouterr().out
    main([str(tmp_path), "--apply"])
    assert not (tmp_path / "old.tmp").exists()
    assert (tmp_path / "new.tmp").exists()


def test_human_size():
    assert human_size(2048) == "2.0 KB"
