import os
from datetime import datetime
from pathlib import Path

import backup_rotator as br
import pytest


def make_backups(folder, stamps, kind="dir"):
    for stamp in stamps:
        path = folder / f"project-{stamp}"
        if kind == "dir":
            path.mkdir(parents=True)
            (path / "data.txt").write_text(stamp)
        else:
            path.with_suffix(".zip").write_text(stamp)


STAMPS = ["20261101-090000", "20261102-090000", "20261103-090000", "20261104-090000",
          "20261105-090000"]


def test_entry_time_prefers_the_name_then_the_file_date(tmp_path):
    named = tmp_path / "project-20261101-090530"
    named.mkdir()
    assert br.entry_time(named) == (datetime(2026, 11, 1, 9, 5, 30), "name")
    dated = tmp_path / "backup_2026-02-03.zip"
    dated.write_text("x")
    assert br.entry_time(dated) == (datetime(2026, 2, 3, 0, 0, 0), "name")
    plain = tmp_path / "latest"
    plain.write_text("x")
    os.utime(plain, (1_700_000_000, 1_700_000_000))
    when, source = br.entry_time(plain)
    assert source == "file date" and when == datetime.fromtimestamp(1_700_000_000)
    impossible = tmp_path / "x-20261399-250000"
    impossible.write_text("x")
    assert br.entry_time(impossible)[1] == "file date"


def entries(*stamps):
    return [(datetime.strptime(s, "%Y%m%d-%H%M%S"), Path(f"b-{s}")) for s in stamps]


def test_choose_keeps_the_newest_n():
    kept, doomed = br.choose(entries(*STAMPS), 2)
    assert [p.name for _, p, _ in kept] == ["b-20261105-090000", "b-20261104-090000"]
    assert [p.name for _, p in doomed] == [
        "b-20261103-090000", "b-20261102-090000", "b-20261101-090000"]
    kept_all, none = br.choose(entries(*STAMPS), 10)
    assert len(kept_all) == 5 and none == []


def test_choose_keep_monthly_adds_one_per_month():
    stamps = ["20260815-090000", "20260820-090000", "20260915-090000", "20261001-090000",
              "20261101-090000", "20261102-090000"]
    kept, doomed = br.choose(entries(*stamps), 1, keep_monthly=3)
    names = {p.name: why for _, p, why in kept}
    assert names == {"b-20261102-090000": "newest 1", "b-20261001-090000": "latest of 2026-10",
                     "b-20260915-090000": "latest of 2026-09"}
    assert "b-20260820-090000" in [p.name for _, p in doomed]  # August is beyond 3 months


def test_dry_run_deletes_nothing(tmp_path, capsys):
    make_backups(tmp_path, STAMPS)
    assert br.main([str(tmp_path), "--pattern", "project-*", "--keep", "3"]) == 0
    out = capsys.readouterr().out
    assert "5 backup(s) match 'project-*': keeping 3, removing 2." in out
    assert "remove  project-20261101-090000" in out and "Dry run" in out
    assert len(list(tmp_path.iterdir())) == 5


def test_apply_removes_the_oldest_folders_and_leaves_everything_else(tmp_path, capsys):
    make_backups(tmp_path, STAMPS)
    (tmp_path / "documents-20261101-090000").mkdir()
    (tmp_path / "keep-me.txt").write_text("not a backup")
    assert br.main([str(tmp_path), "--pattern", "project-*", "--keep", "3", "--apply"]) == 0
    left = sorted(p.name for p in tmp_path.iterdir())
    assert left == ["documents-20261101-090000", "keep-me.txt", "project-20261103-090000",
                    "project-20261104-090000", "project-20261105-090000"]
    assert "Removed 2 backup(s)" in capsys.readouterr().out


def test_works_on_single_file_backups(tmp_path):
    make_backups(tmp_path, STAMPS, kind="file")
    assert br.main([str(tmp_path), "--pattern", "*.zip", "--keep", "1", "--apply"]) == 0
    assert [p.name for p in tmp_path.iterdir()] == ["project-20261105-090000.zip"]


def test_symlinked_backup_is_unlinked_not_followed(tmp_path):
    target = tmp_path / "precious"
    target.mkdir()
    (target / "keep.txt").write_text("keep")
    backups = tmp_path / "backups"
    backups.mkdir()
    make_backups(backups, ["20261105-090000"])
    link = backups / "project-20261101-090000"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("not allowed to create symlinks")
    assert br.main([str(backups), "--pattern", "project-*", "--keep", "1", "--apply"]) == 0
    assert not link.exists() and (target / "keep.txt").read_text() == "keep"


def test_safety_checks(tmp_path, capsys):
    make_backups(tmp_path, STAMPS)
    for args in (["--keep", "0"], ["--keep", "1", "--keep-monthly", "-1"],
                 ["--keep", "1", "--pattern", "../*"]):
        with pytest.raises(SystemExit):
            br.main([str(tmp_path), *(["--pattern", "p*"] if "--pattern" not in args else []),
                     *args])
    with pytest.raises(SystemExit):
        br.main([str(tmp_path / "gone"), "--pattern", "*", "--keep", "1"])
    assert br.main([str(tmp_path), "--pattern", "nothing-*", "--keep", "1"]) == 1
    assert len(list(tmp_path.iterdir())) == 5


def test_nothing_to_prune_and_size_report(tmp_path, capsys):
    make_backups(tmp_path, STAMPS[:2])
    assert br.main([str(tmp_path), "--pattern", "project-*", "--keep", "5"]) == 0
    assert "Nothing to prune." in capsys.readouterr().out
    assert br.size_of(tmp_path / "project-20261101-090000") == len("20261101-090000")
    assert br.human_size(2048) == "2.0 KB"
