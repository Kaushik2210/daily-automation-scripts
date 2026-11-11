import os
from datetime import datetime
from pathlib import Path

import backup_script as bs
import pytest

NOW = "2026-11-10T09:30:00"


@pytest.fixture
def project(tmp_path):
    src = tmp_path / "project"
    (src / "src").mkdir(parents=True)
    (src / "node_modules" / "dep").mkdir(parents=True)
    (src / "empty").mkdir()
    (src / "README.md").write_text("hello")
    (src / "src" / "app.py").write_text("print(1)")
    (src / "src" / "cache.pyc").write_bytes(b"\x00" * 10)
    (src / "node_modules" / "dep" / "index.js").write_text("x")
    return src


def test_human_size():
    assert [bs.human_size(n) for n in (5, 2048, 3 * 1024 ** 3)] == ["5 B", "2.0 KB", "3.0 GB"]


def test_is_excluded_matches_names_and_paths():
    assert bs.is_excluded(Path("a/node_modules/x.js"), ["node_modules"])
    assert bs.is_excluded(Path("a/b.pyc"), ["*.pyc"])
    assert bs.is_excluded(Path("docs/private/key.txt"), ["docs/private/*"])
    assert not bs.is_excluded(Path("src/app.py"), ["*.pyc", "node_modules"])


def test_scan_counts_files_folders_and_skips(project):
    files, folders, skipped, total = bs.scan(project, ["node_modules", "*.pyc"])
    assert [f.as_posix() for f in files] == ["README.md", "src/app.py"]
    assert [f.as_posix() for f in folders] == ["empty"]
    assert total == len("hello") + len("print(1)")
    assert skipped == 2  # the node_modules folder (not each file inside it) and cache.pyc


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="no symlinks here")
def test_symlinks_are_skipped(project):
    try:
        (project / "link.txt").symlink_to(project / "README.md")
    except OSError:
        pytest.skip("not allowed to create symlinks")
    files, _, skipped, _ = bs.scan(project, [])
    assert "link.txt" not in [f.as_posix() for f in files] and skipped >= 1


def test_backup_name():
    assert bs.backup_name(Path("/data/project"), datetime(2026, 11, 10, 9, 30, 5)) == (
        "project-20261110-093005")


def test_dry_run_copies_nothing(project, tmp_path, capsys):
    dest = tmp_path / "backups"
    assert bs.main([str(project), "--dest", str(dest), "--now", NOW]) == 0
    out = capsys.readouterr().out
    assert "project-20261110-093000" in out and "would copy README.md" in out
    assert "Dry run" in out and not dest.exists()


def test_apply_makes_a_faithful_copy_with_excludes(project, tmp_path, capsys):
    dest = tmp_path / "backups"
    assert bs.main([str(project), "--dest", str(dest), "--now", NOW, "--apply",
                    "--exclude", "node_modules", "--exclude", "*.pyc"]) == 0
    backup = dest / "project-20261110-093000"
    assert (backup / "README.md").read_text() == "hello"
    assert (backup / "src" / "app.py").read_text() == "print(1)"
    assert (backup / "empty").is_dir()
    assert not (backup / "node_modules").exists() and not (backup / "src" / "cache.pyc").exists()
    assert not list(dest.glob("*.partial"))
    assert (backup / "README.md").stat().st_mtime == pytest.approx(
        (project / "README.md").stat().st_mtime, abs=2)


def test_existing_backup_is_never_overwritten(project, tmp_path, capsys):
    dest = tmp_path / "backups"
    args = [str(project), "--dest", str(dest), "--now", NOW, "--apply"]
    assert bs.main(args) == 0
    (dest / "project-20261110-093000" / "README.md").write_text("changed")
    assert bs.main(args) == 1
    assert "already exists" in capsys.readouterr().out
    assert (dest / "project-20261110-093000" / "README.md").read_text() == "changed"


def test_destination_inside_the_source_is_refused(project, capsys):
    assert bs.main([str(project), "--dest", str(project / "backups"), "--apply"]) == 1
    assert "can't be inside" in capsys.readouterr().out
    assert not (project / "backups").exists()


def test_failed_copy_leaves_no_partial_folder(project, tmp_path, monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(bs.shutil, "copy2", boom)
    dest = tmp_path / "backups"
    assert bs.main([str(project), "--dest", str(dest), "--now", NOW, "--apply"]) == 1
    assert "failed: disk full" in capsys.readouterr().out
    assert list(dest.iterdir()) == []


def test_bad_inputs(tmp_path, project, capsys):
    assert bs.main([str(tmp_path / "gone"), "--dest", str(tmp_path / "b")]) == 1
    assert "not a folder" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        bs.main([str(project), "--dest", str(tmp_path / "b"), "--now", "yesterday"])
    with pytest.raises(SystemExit):
        bs.main([str(project)])
