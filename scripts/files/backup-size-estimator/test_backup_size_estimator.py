from pathlib import Path

import backup_size_estimator as bse
import pytest


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "project"
    for rel, size in {"notes.txt": 1000, "src/app.py": 3000, "photos/a.jpg": 5000,
                      "photos/b.jpg": 4000, "data.bin": 2000, "node_modules/x/dep.js": 9000,
                      "debug.log": 700}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(b"x" * size)
    return root


def test_human_size_and_is_excluded():
    assert bse.human_size(1536) == "1.5 KB"
    assert bse.is_excluded("a/node_modules/x.js", ["node_modules"])
    assert not bse.is_excluded("src/app.py", ["node_modules", "*.log"])


def test_kind_of_classifies_by_extension():
    assert [bse.kind_of(Path(n)) for n in ("a.TXT", "b.jpg", "c.bin", "noext")] == [
        "text", "packed", "other", "other"]


def test_scan_counts_files_folders_and_excluded_bytes(tree):
    files, skipped, skipped_bytes, folders = bse.scan(tree, ["node_modules", "*.log"])
    assert sorted(rel for rel, _ in files) == [
        "data.bin", "notes.txt", "photos/a.jpg", "photos/b.jpg", "src/app.py"]
    assert skipped == 2 and skipped_bytes == 9000 + 700
    assert folders == 2  # photos and src


def test_estimate_applies_the_per_kind_ratios():
    raw, packed, per_kind = bse.estimate([("a.txt", 1000), ("b.jpg", 1000), ("c.bin", 1000)])
    assert raw == 3000 and per_kind == {"text": 1000, "packed": 1000, "other": 1000}
    assert packed == int(1000 * 0.25 + 1000 * 1.0 + 1000 * 0.7)


def test_free_space_walks_up_to_an_existing_parent(tmp_path):
    assert bse.free_space(tmp_path / "not" / "yet" / "there") > 0


def test_report_for_a_folder(tree, capsys):
    args = [str(tree), "--exclude", "node_modules", "--exclude", "*.log", "--top", "2"]
    assert bse.main(args) == 0
    out = capsys.readouterr().out
    assert out.startswith("5 file(s) in 2 folder(s): 14.6 KB")
    assert "Excluded 2 item(s) worth 9.5 KB." in out
    assert "a compressed archive about" in out
    assert out.index("project/photos/a.jpg") < out.index("project/photos/b.jpg")
    assert "project/data.bin" not in out.split("Biggest files:")[1].split("By file type")[0]
    assert ".jpg" in out.split("By file type:")[1]


def test_several_folders_are_combined(tree, tmp_path, capsys):
    other = tmp_path / "other"
    other.mkdir()
    (other / "one.txt").write_bytes(b"y" * 100)
    assert bse.main([str(tree), str(other), "--exclude", "node_modules", "--top", "20"]) == 0
    out = capsys.readouterr().out
    assert "other/one.txt" in out and out.startswith("7 file(s) in")


def test_destination_check_fits_or_not(tree, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bse, "free_space", lambda dest: 10 ** 9)
    assert bse.main([str(tree), "--dest", str(tmp_path / "bk")]) == 0
    assert "the backup fits." in capsys.readouterr().out
    monkeypatch.setattr(bse, "free_space", lambda dest: 20_000)
    assert bse.main([str(tree), "--dest", str(tmp_path / "bk")]) == 0
    assert "fits only if compressed" in capsys.readouterr().out
    monkeypatch.setattr(bse, "free_space", lambda dest: 100)
    assert bse.main([str(tree), "--dest", str(tmp_path / "bk")]) == 1
    assert "does NOT fit" in capsys.readouterr().out
    monkeypatch.setattr(bse, "free_space", lambda dest: None)
    assert bse.main([str(tree), "--dest", str(tmp_path / "bk")]) == 0
    assert "Couldn't read the free space" in capsys.readouterr().out


def test_nothing_to_back_up_and_bad_input(tree, tmp_path, capsys):
    assert bse.main([str(tree), "--exclude", "*"]) == 1
    assert "nothing to back up" in capsys.readouterr().out
    empty = tmp_path / "empty"
    empty.mkdir()
    assert bse.main([str(empty)]) == 1
    with pytest.raises(SystemExit):
        bse.main([str(tmp_path / "gone")])
