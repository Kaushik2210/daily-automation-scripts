import json
import shutil
import subprocess

import git_large_file_finder as glf
import pytest

LISTING = """blob aaa1 5000000 data/big.csv
blob aaa2 7000000 data/big.csv
blob aaa2 7000000 copy/other.csv
blob bbb1 2000000 video.mp4
blob ccc1 100 tiny.txt
tree ddd1 50 src
commit eee1 200
junk line
"""


@pytest.mark.parametrize("text,size", [("10", 10), ("2k", 2048), ("1.5M", 1572864),
                                       ("1gb", 1024**3), (" 3 MiB ", 3 * 1024**2)])
def test_parse_size(text, size):
    assert glf.parse_size(text) == size


def test_parse_size_rejects_nonsense():
    with pytest.raises(ValueError):
        glf.parse_size("big")


def test_human():
    assert glf.human(500) == "500 B" and glf.human(2048) == "2.0 KB"
    assert glf.human(5 * 1024**2) == "5.0 MB" and glf.human(3 * 1024**3) == "3.0 GB"


def test_parse_objects_keeps_only_blobs():
    blobs = glf.parse_objects(LISTING)
    assert [b[2] for b in blobs] == ["data/big.csv", "data/big.csv", "copy/other.csv",
                                     "video.mp4", "tiny.txt"]


def test_summarise_groups_versions_and_counts_identical_blobs_once():
    entries = glf.summarise(glf.parse_objects(LISTING), {"video.mp4"})
    top = entries[0]
    assert top["path"] == "data/big.csv" and top["versions"] == 2
    assert top["largest"] == 7000000 and top["total"] == 12000000 and top["in_head"] is False
    assert "copy/other.csv" not in [e["path"] for e in entries]  # same blob as aaa2
    assert next(e for e in entries if e["path"] == "video.mp4")["in_head"] is True


def test_cli_from_file(tmp_path, capsys):
    saved = tmp_path / "o.txt"
    saved.write_text(LISTING)
    assert glf.main(["--from-file", str(saved), "--min-size", "1M"]) == 0
    out = capsys.readouterr().out
    assert "2 file(s) at or above 1.0 MB" in out and "tiny.txt" not in out
    assert "2 versions" in out
    assert glf.main(["--from-file", str(saved), "--format", "json", "--top", "1"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["count"] == 2 and data["files"][0]["path"] == "data/big.csv"
    assert glf.main(["--from-file", str(saved), "--min-size", "1G"]) == 0
    assert "Nothing at or above" in capsys.readouterr().out
    assert glf.main(["--from-file", str(tmp_path / "none.txt")]) == 1
    with pytest.raises(SystemExit):
        glf.main(["--from-file", str(saved), "--min-size", "huge"])


@pytest.mark.skipif(not shutil.which("git"), reason="git is not installed")
def test_real_history_finds_deleted_big_file(tmp_path, capsys, monkeypatch):
    for key, value in (("NAME", "T"), ("EMAIL", "t@example.com")):
        monkeypatch.setenv(f"GIT_AUTHOR_{key}", value)
        monkeypatch.setenv(f"GIT_COMMITTER_{key}", value)

    def run(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    run("init", "-q", "-b", "main")
    (tmp_path / "old.bin").write_bytes(bytes(range(256)) * 2000)
    (tmp_path / "keep.bin").write_bytes(bytes(reversed(range(256))) * 3000)
    run("add", ".")
    run("commit", "-q", "-m", "add")
    (tmp_path / "old.bin").unlink()
    run("add", "-A")
    run("commit", "-q", "-m", "drop")
    base = ["--repo", str(tmp_path), "--min-size", "100k"]
    assert glf.main(base) == 0
    out = capsys.readouterr().out
    assert "old.bin" in out and "removed" in out and "keep.bin" in out and "in latest" in out
    assert "git filter-repo --path old.bin" in out
    assert glf.main([*base, "--only-removed", "--format", "json"]) == 0
    assert [f["path"] for f in json.loads(capsys.readouterr().out)["files"]] == ["old.bin"]
    assert glf.main([*base, "--ref", "main", "--only-removed"]) == 0  # a named ref works too
    assert "old.bin" in capsys.readouterr().out
    assert glf.main([*base, "--fail-over", "500k"]) == 1
    assert glf.main(["--repo", str(tmp_path / "missing")]) == 1
