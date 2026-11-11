import io
import tarfile
from datetime import datetime

import pytest
import tar_archiver as ta

NOW = datetime(2026, 11, 10, 9, 30, 0)


@pytest.fixture
def project(tmp_path):
    src = tmp_path / "project"
    for rel, text in {"README.md": "hello " * 40, "src/app.py": "print(1)\n" * 30,
                      "build/out.bin": "x" * 50, "debug.log": "noise"}.items():
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(text)
    return src


def test_compression_for_extensions():
    names = ("a.tar.gz", "a.TGZ", "a.tar.bz2", "a.tar.xz", "a.tar")
    assert [ta.compression_for(n) for n in names] == ["gz", "gz", "bz2", "xz", ""]
    with pytest.raises(ValueError):
        ta.compression_for("a.zip")


def test_collect_stores_folders_under_their_name_and_prunes(project):
    entries = ta.collect([project], ["build", "*.log"])
    assert [name for _, name in entries] == ["project/README.md", "project/src/app.py"]
    single = ta.collect([project / "README.md"], [])
    assert [name for _, name in single] == ["README.md"]


def test_dry_run_creates_nothing(project, tmp_path, capsys):
    out = tmp_path / "a.tar.gz"
    assert ta.main(["create", str(project), "--out", str(out), "--exclude", "build"]) == 0
    text = capsys.readouterr().out
    assert "would add project/README.md" in text and "plus MANIFEST.json" in text
    assert not out.exists()


@pytest.mark.parametrize("suffix", [".tar.gz", ".tar.bz2", ".tar.xz", ".tar"])
def test_create_makes_a_readable_archive_with_a_manifest_first(project, tmp_path, suffix):
    out = tmp_path / f"a{suffix}"
    assert ta.main(["create", str(project), "--out", str(out), "--exclude", "build", "--exclude",
                    "*.log", "--now", "2026-11-10T09:30:00", "--apply"]) == 0
    with tarfile.open(out) as tar:
        names = tar.getnames()
        assert names == [ta.MANIFEST, "project/README.md", "project/src/app.py"]
        info = tar.getmember("project/README.md")
        assert info.uid == 0 and info.uname == "" and info.gname == ""
    manifest = ta.read_manifest(out)
    assert manifest["created"] == "2026-11-10T09:30:00"
    assert [f["path"] for f in manifest["files"]] == ["project/README.md", "project/src/app.py"]
    assert manifest["files"][0]["size"] == len("hello " * 40)
    assert not list(tmp_path.glob("*.partial"))


def test_list_and_verify_a_good_archive(project, tmp_path, capsys):
    out = tmp_path / "a.tar.gz"
    ta.main(["create", str(project), "--out", str(out), "--exclude", "build", "--apply"])
    capsys.readouterr()
    assert ta.main(["list", str(out)]) == 0
    listing = capsys.readouterr().out
    assert "project/README.md" in listing and "3 file(s)" in listing
    assert ta.main(["verify", str(out)]) == 0
    assert "OK - every file matches" in capsys.readouterr().out


def rebuild(archive, edit):
    """Rewrite an archive after letting `edit(name, data)` change or drop members."""
    members = []
    with tarfile.open(archive) as tar:
        for m in tar:
            data = tar.extractfile(m).read() if m.isfile() else b""
            members.append((m, data))
    with tarfile.open(archive, "w:gz") as tar:
        for m, data in members:
            result = edit(m.name, data)
            if result is None:
                continue
            m.size = len(result)
            tar.addfile(m, io.BytesIO(result))


def test_verify_catches_damaged_missing_and_unlisted_files(project, tmp_path, capsys):
    out = tmp_path / "a.tar.gz"
    ta.main(["create", str(project), "--out", str(out), "--apply"])
    capsys.readouterr()

    def tamper(name, data):
        if name == "project/README.md":
            return data.replace(b"hello", b"HELLO")
        if name == "project/src/app.py":
            return None
        return data

    rebuild(out, tamper)
    checked, missing, damaged, unlisted = ta.verify_archive(out)
    assert (missing, damaged) == (["project/src/app.py"], ["project/README.md"])
    assert ta.main(["verify", str(out)]) == 1
    text = capsys.readouterr().out
    assert "Missing (1)" in text and "Damaged (1)" in text and "PROBLEMS FOUND" in text


def test_existing_archive_never_overwritten_and_clashes_refused(project, tmp_path, capsys):
    out = tmp_path / "a.tar.gz"
    out.write_bytes(b"precious")
    assert ta.main(["create", str(project), "--out", str(out), "--apply"]) == 1
    assert out.read_bytes() == b"precious"
    other = tmp_path / "other" / "project"
    other.mkdir(parents=True)
    (other / "README.md").write_text("x")
    assert ta.main(["create", str(project / "README.md"), str(other / "README.md"), "--out",
                    str(tmp_path / "b.tar.gz"), "--apply"]) == 1
    assert "same name" in capsys.readouterr().out


def test_failed_write_leaves_nothing_behind(project, tmp_path, monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(ta.tarfile.TarFile, "add", boom)
    out = tmp_path / "a.tar.gz"
    assert ta.main(["create", str(project), "--out", str(out), "--apply"]) == 1
    assert "disk full" in capsys.readouterr().err
    assert not out.exists() and not list(tmp_path.glob("*.partial"))


def test_archive_inside_the_source_skips_itself(project, capsys):
    out = project / "backup.tar.gz"
    assert ta.main(["create", str(project), "--out", str(out), "--apply"]) == 0
    assert "project/backup.tar.gz" not in [f["path"] for f in ta.read_manifest(out)["files"]]


def test_argument_errors_and_bad_archives(project, tmp_path, capsys):
    for args in (["create", str(project)], ["create", str(project), "--out", "x.zip"],
                 ["create", str(tmp_path / "gone"), "--out", "x.tar.gz"],
                 ["list"], ["verify", str(project)], ["create", str(project), "--out", "x.tar.gz",
                                                       "--now", "never"]):
        with pytest.raises(SystemExit):
            ta.main(args)
    bad = tmp_path / "bad.tar.gz"
    bad.write_bytes(b"not a tar")
    assert ta.main(["verify", str(bad)]) == 1
    plain = tmp_path / "plain.tar"
    with tarfile.open(plain, "w") as tar:
        tar.addfile(tarfile.TarInfo("a.txt"), io.BytesIO(b""))
    assert ta.main(["list", str(plain)]) == 1
    assert "Couldn't read the archive" in capsys.readouterr().err
