import json

import pytest
import snapshot_differ as sd


def snap(**files):
    entries = {name: {"size": len(text), "sha256": f"h-{text}"} for name, text in files.items()}
    return {"root": "r", "created": "2026-01-01T00:00:00", "files": entries}


def test_human_size_handles_negative_changes():
    assert [sd.human_size(n) for n in (0, 1536, -2048)] == ["0 B", "1.5 KB", "-2.0 KB"]


def test_compare_added_removed_changed_unchanged():
    old = snap(**{"keep.txt": "same", "edit.txt": "one", "gone.txt": "bye"})
    new = snap(**{"keep.txt": "same", "edit.txt": "two", "fresh.txt": "hello"})
    result = sd.compare(old, new)
    assert result == {"added": ["fresh.txt"], "removed": ["gone.txt"], "changed": ["edit.txt"],
                      "moved": [], "unchanged": 1}


def test_moves_are_matched_by_content():
    old = snap(**{"docs/a.md": "alpha", "b.txt": "beta", "same-twice-1": "dup"})
    new = snap(**{"guides/a.md": "alpha", "b.txt": "beta", "x/dup": "dup", "same-twice-1": "dup"})
    result = sd.compare(old, new)
    assert result["moved"] == [("docs/a.md", "guides/a.md")]
    assert result["added"] == ["x/dup"] and result["removed"] == []


def test_size_only_snapshots_compare_by_size():
    old = {"files": {"a": {"size": 3}, "b": {"size": 5}}}
    new = {"files": {"a": {"size": 3}, "b": {"size": 6}}}
    assert sd.compare(old, new)["changed"] == ["b"]


def test_take_snapshot_hashes_excludes_and_sorts(tmp_path):
    (tmp_path / "b.txt").write_text("beta")
    (tmp_path / "a.txt").write_text("alpha")
    (tmp_path / "skip.log").write_text("noise")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.txt").write_text("gamma")
    snapshot = sd.take_snapshot(tmp_path, ["*.log"])
    assert list(snapshot["files"]) == ["a.txt", "b.txt", "sub/c.txt"]
    entry = snapshot["files"]["a.txt"]
    assert entry["size"] == 5 and len(entry["sha256"]) == 64
    assert "sha256" not in sd.take_snapshot(tmp_path, [], quick=True)["files"]["a.txt"]


def test_snapshot_then_compare_through_the_cli(tmp_path, capsys):
    folder, saved = tmp_path / "proj", tmp_path / "before.json"
    folder.mkdir()
    (folder / "a.txt").write_text("alpha")
    (folder / "b.txt").write_text("beta")
    assert sd.main(["snapshot", str(folder), "--out", str(saved)]) == 0
    assert "Saved a snapshot of 2 file(s)" in capsys.readouterr().out
    assert sd.main(["compare", str(saved), str(folder)]) == 0
    assert "The snapshots are identical." in capsys.readouterr().out
    (folder / "a.txt").write_text("alpha edited")
    (folder / "b.txt").rename(folder / "renamed.txt")
    (folder / "new.txt").write_text("brand new")
    assert sd.main(["compare", str(saved), str(folder)]) == 1
    out = capsys.readouterr().out
    assert "Added (1):\n  + new.txt" in out and "Changed (1):\n  ~ a.txt" in out
    assert "Moved or renamed (1):\n  > b.txt -> renamed.txt" in out
    assert "0 unchanged" in out


def test_compare_two_saved_snapshots(tmp_path, capsys):
    (tmp_path / "old.json").write_text(json.dumps(snap(**{"a": "1", "b": "22"})))
    (tmp_path / "new.json").write_text(json.dumps(snap(**{"a": "1"})))
    assert sd.main(["compare", str(tmp_path / "old.json"), str(tmp_path / "new.json")]) == 1
    out = capsys.readouterr().out
    assert "Removed (1):\n  - b" in out and "Size change: -2 B." in out


def test_never_overwrites_an_existing_snapshot(tmp_path, capsys):
    folder, out = tmp_path / "proj", tmp_path / "snap.json"
    folder.mkdir()
    out.write_text("keep")
    assert sd.main(["snapshot", str(folder), "--out", str(out)]) == 1
    assert out.read_text() == "keep"


def test_bad_arguments_and_files(tmp_path, capsys):
    folder = tmp_path / "proj"
    folder.mkdir()
    for args in (["snapshot", str(folder)], ["snapshot", str(tmp_path / "gone"), "--out", "x.json"],
                 ["compare", str(folder)], ["compare", str(folder), str(folder), str(folder)]):
        with pytest.raises(SystemExit):
            sd.main(args)
    bad = tmp_path / "bad.json"
    bad.write_text('{"nope": 1}')
    assert sd.main(["compare", str(bad), str(folder)]) == 1
    bad.write_text("{broken")
    assert sd.main(["compare", str(bad), str(folder)]) == 1
    assert "Couldn't read a snapshot" in capsys.readouterr().err
