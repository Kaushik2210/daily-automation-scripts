import json
import os
from pathlib import Path

import incremental_backup as ib
import pytest

NOW = "2026-11-10T09:30:00"


def write(path, text, mtime=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if mtime:
        os.utime(path, (mtime, mtime))


@pytest.fixture
def folders(tmp_path):
    src, dest = tmp_path / "src", tmp_path / "bak"
    write(src / "a.txt", "alpha", 1_700_000_000)
    write(src / "docs" / "b.md", "beta", 1_700_000_000)
    write(src / "cache" / "tmp.bin", "junk", 1_700_000_000)
    return src, dest


def run(src, dest, *extra):
    return ib.main([str(src), "--dest", str(dest), "--exclude", "cache", "--now", NOW, *extra])


def test_is_excluded_and_human_size():
    assert ib.is_excluded(Path("x/cache/y.bin"), ["cache"]) and not ib.is_excluded(
        Path("x/y.bin"), ["cache"])
    assert ib.human_size(1536) == "1.5 KB"


def test_scan_skips_excluded_and_hashes_on_request(folders):
    src, _ = folders
    plain = ib.scan(src, ["cache"])
    assert sorted(plain) == ["a.txt", "docs/b.md"] and "sha256" not in plain["a.txt"]
    hashed = ib.scan(src, ["cache"], use_hash=True)
    assert hashed["a.txt"]["sha256"] == ib.sha256(src / "a.txt")
    assert plain["a.txt"] == {"size": 5, "mtime": 1_700_000_000.0}


def test_plan_detects_new_changed_removed_and_missing_backups(tmp_path):
    dest = tmp_path / "bak"
    (dest).mkdir()
    for name in ("same", "grew", "touched"):
        (dest / name).write_text("x")
    previous = {"same": {"size": 1, "mtime": 100.0}, "grew": {"size": 1, "mtime": 100.0},
                "touched": {"size": 1, "mtime": 100.0}, "gone": {"size": 1, "mtime": 1.0},
                "lost": {"size": 1, "mtime": 100.0}}
    current = {"same": {"size": 1, "mtime": 101.5}, "grew": {"size": 9, "mtime": 100.0},
               "touched": {"size": 1, "mtime": 500.0}, "fresh": {"size": 3, "mtime": 1.0},
               "lost": {"size": 1, "mtime": 100.0}}
    new, changed, removed = ib.plan(current, previous, dest)
    assert sorted(new) == ["fresh", "lost"]  # 'lost' is in the record but missing from the backup
    assert sorted(changed) == ["grew", "touched"]  # 'same' moved by under the 2 s tolerance
    assert removed == ["gone"]


def test_plan_hash_mode_ignores_timestamps(tmp_path):
    (tmp_path / "f").write_text("x")
    previous = {"f": {"size": 1, "mtime": 1.0, "sha256": "aa"}}
    same = {"f": {"size": 1, "mtime": 999.0, "sha256": "aa"}}
    different = {"f": {"size": 1, "mtime": 1.0, "sha256": "bb"}}
    assert ib.plan(same, previous, tmp_path, use_hash=True) == ([], [], [])
    assert ib.plan(different, previous, tmp_path, use_hash=True)[1] == ["f"]


def test_dry_run_writes_nothing(folders, capsys):
    src, dest = folders
    assert run(src, dest) == 0
    out = capsys.readouterr().out
    assert "2 file(s) in" in out and "2 new, 0 changed" in out and "Dry run" in out
    assert not dest.exists()


def test_first_run_then_nothing_then_only_the_changes(folders, capsys):
    src, dest = folders
    assert run(src, dest, "--apply") == 0
    assert (dest / "docs" / "b.md").read_text() == "beta" and not (dest / "cache").exists()
    assert sorted(json.loads((dest / ib.MANIFEST).read_text())["files"]) == ["a.txt", "docs/b.md"]
    capsys.readouterr()
    assert run(src, dest, "--apply") == 0
    assert "0 new, 0 changed, 2 unchanged" in capsys.readouterr().out
    write(src / "a.txt", "alpha edited", 1_700_000_500)
    write(src / "c.txt", "gamma", 1_700_000_500)
    assert run(src, dest, "--apply") == 0
    out = capsys.readouterr().out
    assert "1 new, 1 changed, 1 unchanged" in out and "+ c.txt" in out and "~ a.txt" in out
    assert (dest / "a.txt").read_text() == "alpha edited"


def test_changed_files_keep_their_old_version_in_history(folders):
    src, dest = folders
    run(src, dest, "--apply")
    write(src / "a.txt", "alpha v2", 1_700_000_900)
    run(src, dest, "--apply")
    assert (dest / ib.HISTORY / "20261110-093000" / "a.txt").read_text() == "alpha"
    write(src / "a.txt", "alpha v3", 1_700_001_900)
    run(src, dest, "--apply", "--no-history")
    assert (dest / "a.txt").read_text() == "alpha v3"
    assert (dest / ib.HISTORY / "20261110-093000" / "a.txt").read_text() == "alpha"  # untouched


def test_removed_source_files_stay_in_the_backup(folders, capsys):
    src, dest = folders
    run(src, dest, "--apply")
    (src / "docs" / "b.md").unlink()
    capsys.readouterr()
    assert run(src, dest, "--apply") == 0
    assert "1 file(s) were removed from the source; their backups are kept." in (
        capsys.readouterr().out)
    assert (dest / "docs" / "b.md").read_text() == "beta"


def test_bad_arguments_and_broken_record(folders, tmp_path, capsys):
    src, dest = folders
    with pytest.raises(SystemExit):
        ib.main([str(tmp_path / "gone"), "--dest", str(dest)])
    with pytest.raises(SystemExit):
        ib.main([str(src), "--dest", str(src / "inside")])
    dest.mkdir()
    (dest / ib.MANIFEST).write_text("{broken")
    assert run(src, dest) == 1
    assert "previous backup record" in capsys.readouterr().err
