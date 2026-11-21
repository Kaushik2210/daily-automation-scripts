import os
import time
from pathlib import Path

import download_watcher as dw
import pytest


def touch(path, age=100, text="x"):
    path.write_text(text)
    stamp = time.time() - age
    os.utime(path, (stamp, stamp))
    return path


@pytest.mark.parametrize("name,category", [
    ("photo.JPG", "Images"), ("report.pdf", "Documents"), ("data.csv", "Data"),
    ("backup.zip", "Archives"), ("song.mp3", "Audio"), ("clip.mkv", "Video"),
    ("setup.exe", "Installers"), ("script.py", "Code"), ("mystery", "Other"),
    ("weird.xyz", "Other"), ("archive.tar.gz", "Archives")])
def test_category_of(name, category):
    assert dw.category_of(Path(name)) == category


def test_free_name_never_overwrites(tmp_path):
    target = tmp_path / "a.txt"
    assert dw.free_name(target) == target
    touch(target)
    assert dw.free_name(target).name == "a (1).txt"
    touch(tmp_path / "a (1).txt")
    assert dw.free_name(target).name == "a (2).txt"


def make_downloads(tmp_path):
    for name in ["a.pdf", "b.jpg", "c.zip", "weird"]:
        touch(tmp_path / name)
    touch(tmp_path / "big.iso.crdownload")
    touch(tmp_path / "fresh.png", age=0)
    touch(tmp_path / ".hidden")
    (tmp_path / "Images").mkdir()
    touch(tmp_path / "Images" / "b.jpg")  # same name already sorted
    return tmp_path


def test_plan_skips_partial_hidden_fresh_and_folders(tmp_path):
    moves, skipped = dw.plan(make_downloads(tmp_path), settle=5)
    assert {s.name: t.parent.name for s, t in moves} == {
        "a.pdf": "Documents", "b.jpg": "Images", "c.zip": "Archives", "weird": "Other"}
    assert {name for name, _ in skipped} == {"big.iso.crdownload", "fresh.png", ".hidden"}
    assert [t.name for s, t in moves if s.name == "b.jpg"] == ["b (1).jpg"]


def test_dry_run_then_apply(tmp_path, capsys):
    folder = make_downloads(tmp_path)
    assert dw.main([str(folder)]) == 0
    out = capsys.readouterr().out
    assert "a.pdf -> Documents/" in out and "b.jpg -> Images/ (as b (1).jpg)" in out
    assert "Would move 4 file(s)" in out and (folder / "a.pdf").exists()
    assert dw.main([str(folder), "--apply"]) == 0
    assert "Moved 4 file(s)" in capsys.readouterr().out
    assert (folder / "Documents" / "a.pdf").exists() and not (folder / "a.pdf").exists()
    assert (folder / "Images" / "b.jpg").read_text() == "x"
    assert (folder / "Images" / "b (1).jpg").exists() and (folder / "big.iso.crdownload").exists()
    assert (folder / "fresh.png").exists()
    assert dw.main([str(folder), "--apply"]) == 0
    assert "nothing to sort" in capsys.readouterr().out


def test_watch_mode_runs_until_the_time_limit(tmp_path, capsys):
    touch(tmp_path / "a.txt")
    assert dw.main([str(tmp_path), "--watch", "--seconds", "0.2", "--interval", "0.05",
                    "--apply"]) == 0
    assert (tmp_path / "Documents" / "a.txt").exists()


def test_bad_arguments(tmp_path):
    with pytest.raises(SystemExit):
        dw.main([str(tmp_path / "missing")])
    with pytest.raises(SystemExit):
        dw.main([str(tmp_path), "--interval", "0"])
