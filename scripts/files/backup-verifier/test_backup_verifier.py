import shutil
import zipfile

import backup_verifier as bv
import pytest


@pytest.fixture
def pair(tmp_path):
    src, bak = tmp_path / "project", tmp_path / "backup"
    for rel, text in {"a.txt": "alpha", "docs/b.md": "beta", "src/c.py": "gamma"}.items():
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(text)
    shutil.copytree(src, bak)
    return src, bak


def test_is_excluded():
    assert bv.is_excluded("x/.history/a.txt", [".history"]) and bv.is_excluded("a.log", ["*.log"])
    assert not bv.is_excluded("src/c.py", ["*.log", ".history"])


def test_compare_finds_missing_different_and_extra():
    source = {"same": (1, "h"), "gone": (1, "h"), "edited": (1, "h"), "grew": (1, "h")}
    backup = {"same": (1, "h"), "edited": (1, "other"), "grew": (2, "h"), "new": (1, "h")}
    assert bv.compare(source, backup) == (["gone"], ["edited", "grew"], ["new"])


def test_read_folder_hashes_unless_quick(pair):
    src, _ = pair
    full = bv.read_folder(src, [], quick=False)
    assert full["docs/b.md"][0] == 4 and len(full["docs/b.md"][1]) == 64
    assert bv.read_folder(src, [], quick=True)["docs/b.md"] == (4, None)
    assert "a.txt" not in bv.read_folder(src, ["a.txt"], False)


def test_identical_folders_pass(pair, capsys):
    src, bak = pair
    assert bv.main([str(src), str(bak)]) == 0
    out = capsys.readouterr().out
    assert "Compared 3 source file(s) with 3 in the backup by SHA-256." in out
    assert "OK - the backup matches the source exactly." in out


def test_problems_are_listed_and_fail(pair, capsys):
    src, bak = pair
    (bak / "docs" / "b.md").write_text("BETA")       # same size, different content
    (bak / "src" / "c.py").unlink()                  # missing
    (bak / "extra.log").write_text("x")              # only in the backup
    assert bv.main([str(src), str(bak)]) == 1
    out = capsys.readouterr().out
    assert "Missing from the backup (1):\n  src/c.py" in out
    assert "Different in the backup (1):\n  docs/b.md" in out
    assert "Only in the backup (1):\n  extra.log" in out and "PROBLEMS FOUND" in out


def test_quick_mode_misses_same_size_edits_but_catches_size_changes(pair, capsys):
    src, bak = pair
    (bak / "docs" / "b.md").write_text("BETA")
    assert bv.main([str(src), str(bak), "--quick"]) == 0
    (bak / "docs" / "b.md").write_text("BETA!")
    assert bv.main([str(src), str(bak), "--quick"]) == 1


def test_extras_only_fail_in_strict_mode(pair, capsys):
    src, bak = pair
    (bak / "extra.txt").write_text("x")
    assert bv.main([str(src), str(bak)]) == 0
    assert "also has extra files" in capsys.readouterr().out
    assert bv.main([str(src), str(bak), "--strict"]) == 1


def test_incremental_backup_bookkeeping_is_ignored(pair):
    src, bak = pair
    (bak / ".backup-manifest.json").write_text("{}")
    (bak / ".history" / "20261101").mkdir(parents=True)
    (bak / ".history" / "20261101" / "a.txt").write_text("old")
    assert bv.main([str(src), str(bak), "--strict"]) == 0


def make_zip(path, files, top=None):
    with zipfile.ZipFile(path, "w") as z:
        for name, text in files.items():
            z.writestr(f"{top}/{name}" if top else name, text)
        if top:
            z.writestr(f"{top}/", "")


def test_zip_backups_with_and_without_a_top_folder(pair, tmp_path, capsys):
    src, _ = pair
    files = {"a.txt": "alpha", "docs/b.md": "beta", "src/c.py": "gamma"}
    make_zip(tmp_path / "wrapped.zip", files, top="project")
    make_zip(tmp_path / "flat.zip", files)
    assert bv.main([str(src), str(tmp_path / "wrapped.zip")]) == 0
    assert bv.main([str(src), str(tmp_path / "flat.zip")]) == 0
    broken = {**files, "a.txt": "tampered"}
    make_zip(tmp_path / "bad.zip", broken, top="project")
    assert bv.main([str(src), str(tmp_path / "bad.zip")]) == 1
    assert "Different in the backup (1):\n  a.txt" in capsys.readouterr().out


def test_zip_strip_option_and_corrupt_archive(pair, tmp_path, capsys):
    src, _ = pair
    make_zip(tmp_path / "multi.zip", {"v1/a.txt": "alpha", "v1/docs/b.md": "beta",
                                      "v1/src/c.py": "gamma", "other.txt": "x"})
    assert bv.main([str(src), str(tmp_path / "multi.zip"), "--strip", "v1/"]) == 0
    (tmp_path / "junk.zip").write_bytes(b"not a zip")
    assert bv.main([str(src), str(tmp_path / "junk.zip")]) == 1
    assert "Couldn't read" in capsys.readouterr().err


def test_long_lists_are_trimmed(pair, capsys):
    src, bak = pair
    for i in range(25):
        (src / f"n{i:02}.txt").write_text(str(i))
    assert bv.main([str(src), str(bak)]) == 1
    assert "... and 5 more" in capsys.readouterr().out


def test_bad_arguments(tmp_path):
    with pytest.raises(SystemExit):
        bv.main([str(tmp_path / "gone"), str(tmp_path)])
    with pytest.raises(SystemExit):
        bv.main([str(tmp_path), str(tmp_path / "gone")])
