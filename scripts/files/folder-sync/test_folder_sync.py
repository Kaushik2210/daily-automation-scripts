import os

import folder_sync as fs
import pytest


def write(path, text, mtime=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if mtime:
        os.utime(path, (mtime, mtime))


@pytest.fixture
def pair(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    write(src / "same.txt", "same", 1_700_000_000)
    write(src / "docs" / "new.md", "brand new")
    write(src / "edit.txt", "version two", 1_700_000_500)
    write(dst / "same.txt", "same", 1_700_000_000)
    write(dst / "edit.txt", "version one", 1_700_000_000)
    write(dst / "old" / "gone.txt", "only in the target")
    return src, dst


def test_plan_finds_new_updated_and_extra(pair):
    src, dst = pair
    new, update, extra = fs.make_plan(fs.list_files(src, []), fs.list_files(dst, []), quick=False)
    assert (new, update, extra) == (["docs/new.md"], ["edit.txt"], ["old/gone.txt"])


def test_same_size_edits_are_found_by_content_but_not_by_quick_mode(tmp_path):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    write(a, "AAAA", 1_700_000_000)
    write(b, "BBBB", 1_700_000_000)
    assert fs.differs(a, b, quick=False) and not fs.differs(a, b, quick=True)
    os.utime(a, (1_700_000_100, 1_700_000_100))  # source newer by more than the tolerance
    assert fs.differs(a, b, quick=True)
    os.utime(a, (1_699_999_000, 1_699_999_000))  # source older: not an update
    assert not fs.differs(a, b, quick=True)


def test_dry_run_changes_nothing(pair, capsys):
    src, dst = pair
    assert fs.main([str(src), str(dst)]) == 0
    out = capsys.readouterr().out
    assert "1 to add, 1 to update, 1 only in the target (kept)." in out
    assert "+ docs/new.md" in out and "~ edit.txt" in out and "? old/gone.txt" in out
    assert not (dst / "docs").exists() and (dst / "edit.txt").read_text() == "version one"


def test_apply_copies_and_keeps_extras_without_delete(pair, capsys):
    src, dst = pair
    assert fs.main([str(src), str(dst), "--apply"]) == 0
    assert (dst / "docs" / "new.md").read_text() == "brand new"
    assert (dst / "edit.txt").read_text() == "version two"
    assert (dst / "old" / "gone.txt").exists()
    assert not list(dst.rglob("*.sync-tmp"))
    assert (src / "edit.txt").read_text() == "version two"  # the source is never changed


def test_delete_removes_extras_and_empty_folders(pair, capsys):
    src, dst = pair
    assert fs.main([str(src), str(dst), "--delete", "--apply"]) == 0
    assert not (dst / "old").exists() and (dst / "same.txt").exists()
    assert "1 deleted" in capsys.readouterr().out
    assert fs.main([str(src), str(dst), "--delete"]) == 0
    assert "0 to add, 0 to update, 0 only in the target" in capsys.readouterr().out


def test_empty_source_never_wipes_the_target(tmp_path, capsys):
    src, dst = tmp_path / "src", tmp_path / "dst"
    src.mkdir()
    write(dst / "precious.txt", "keep me")
    assert fs.main([str(src), str(dst), "--delete", "--apply"]) == 1
    assert (dst / "precious.txt").exists() and "would empty the target" in capsys.readouterr().out
    assert fs.main([str(src), str(dst), "--delete", "--apply", "--allow-empty"]) == 0
    assert not (dst / "precious.txt").exists()


def test_missing_target_is_created_and_excludes_apply_to_both_sides(pair, tmp_path):
    src, _ = pair
    write(src / "debug.log", "noise")
    fresh = tmp_path / "fresh"
    assert fs.main([str(src), str(fresh), "--exclude", "*.log", "--apply"]) == 0
    assert (fresh / "docs" / "new.md").exists() and not (fresh / "debug.log").exists()


def test_failed_copy_is_reported_and_leaves_no_temp_file(pair, monkeypatch, capsys):
    src, dst = pair

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(fs.shutil, "copy2", boom)
    assert fs.main([str(src), str(dst), "--apply"]) == 1
    assert "could not copy" in capsys.readouterr().out and not list(dst.rglob("*.sync-tmp"))


def test_unsafe_folder_combinations_are_refused(pair, tmp_path):
    src, dst = pair
    for args in ([str(src), str(src / "inside")], [str(src), str(src)],
                 [str(tmp_path / "gone"), str(dst)]):
        with pytest.raises(SystemExit):
            fs.main(args)
    write(tmp_path / "afile", "x")
    with pytest.raises(SystemExit):
        fs.main([str(src), str(tmp_path / "afile")])
