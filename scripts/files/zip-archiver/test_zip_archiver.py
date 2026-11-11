import zipfile
from pathlib import Path

import pytest
import zip_archiver as za


@pytest.fixture
def project(tmp_path):
    src = tmp_path / "project"
    for rel, text in {"README.md": "hello " * 50, "src/app.py": "print(1)\n" * 40,
                      "src/cache.pyc": "bytecode", "build/out.bin": "x" * 100,
                      ".git/config": "[core]", "notes.log": "log"}.items():
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(text)
    return src


def names(archive):
    with zipfile.ZipFile(archive) as z:
        return sorted(z.namelist())


def test_human_size_and_is_excluded():
    assert za.human_size(2048) == "2.0 KB"
    assert za.is_excluded(Path("a/build/x"), ["build"]) and za.is_excluded(Path("x.log"), ["*.log"])
    assert not za.is_excluded(Path("src/app.py"), ["*.log", "build"])


def test_collect_prefixes_with_the_folder_name_and_prunes(project):
    entries = za.collect(project, ["build", "*.pyc"], set())
    assert [name for _, name in entries] == [
        "project/.git/config", "project/README.md", "project/notes.log", "project/src/app.py"]
    bare = za.collect(project, ["build"], set(), top_folder=False)
    assert "README.md" in [name for _, name in bare]
    single = za.collect(project / "README.md", [], set())
    assert [name for _, name in single] == ["README.md"]


def test_dry_run_creates_no_file(project, tmp_path, capsys):
    out = tmp_path / "out.zip"
    assert za.main([str(project), "--out", str(out), "--exclude-common"]) == 0
    text = capsys.readouterr().out
    assert "would add project/README.md" in text and "Dry run" in text and not out.exists()
    assert ".git" not in text and "cache.pyc" not in text


def test_apply_creates_a_valid_smaller_zip(project, tmp_path, capsys):
    out = tmp_path / "out.zip"
    args = [str(project), "--out", str(out), "--exclude-common", "--exclude", "build",
            "--exclude", "*.log"]
    assert za.main([*args, "--apply"]) == 0
    assert names(out) == ["project/README.md", "project/src/app.py"]
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None and z.read("project/README.md") == b"hello " * 50
    assert "smaller" in capsys.readouterr().out
    assert not list(tmp_path.glob("*.partial"))


def test_existing_zip_is_never_overwritten(project, tmp_path, capsys):
    out = tmp_path / "out.zip"
    out.write_bytes(b"precious")
    assert za.main([str(project), "--out", str(out), "--apply"]) == 1
    assert out.read_bytes() == b"precious" and "already exists" in capsys.readouterr().out


def test_archive_inside_the_source_is_not_zipped_into_itself(project, capsys):
    out = project / "backup.zip"
    assert za.main([str(project), "--out", str(out), "--apply"]) == 0
    assert "project/backup.zip" not in names(out)


def test_several_sources_and_name_clashes(project, tmp_path, capsys):
    other = tmp_path / "other"
    other.mkdir()
    (other / "README.md").write_text("other")
    out = tmp_path / "both.zip"
    both = [str(project), str(other), "--out", str(out), "--exclude", ".git"]
    assert za.main([*both, "--apply"]) == 0
    assert "other/README.md" in names(out) and "project/README.md" in names(out)
    clash = tmp_path / "clash.zip"
    assert za.main([str(project), str(other), "--out", str(clash), "--no-top-folder",
                    "--apply"]) == 1
    assert "same name" in capsys.readouterr().out and not clash.exists()


def test_failed_write_leaves_nothing_behind(project, tmp_path, monkeypatch, capsys):
    def boom(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(zipfile.ZipFile, "write", boom)
    out = tmp_path / "out.zip"
    assert za.main([str(project), "--out", str(out), "--apply"]) == 1
    assert "disk full" in capsys.readouterr().err
    assert not out.exists() and not list(tmp_path.glob("*.partial"))


def test_argument_errors(project, tmp_path):
    for args in ([str(tmp_path / "gone"), "--out", "x.zip"], [str(project), "--out", "x.txt"],
                 [str(project), "--out", "x.zip", "--level", "12"]):
        with pytest.raises(SystemExit):
            za.main(args)
    everything = ["--exclude", "*"]
    assert za.main([str(project), "--out", str(tmp_path / "e.zip"), *everything]) == 1
