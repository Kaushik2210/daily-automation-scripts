import hashlib

from file_hasher import collect, hash_file, main


def test_hash_file_multiple_algorithms(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"abc")
    result = hash_file(f, ["md5", "sha256"])
    assert result["md5"] == hashlib.md5(b"abc").hexdigest()
    assert result["sha256"] == hashlib.sha256(b"abc").hexdigest()


def test_collect_recursive_flag(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "sub" / "b.txt").write_text("y")
    assert [p.name for p in collect([tmp_path], False)] == ["a.txt"]
    assert sorted(p.name for p in collect([tmp_path], True)) == ["a.txt", "b.txt"]


def test_sums_format_matches_sha256sum(tmp_path, capsys):
    f = tmp_path / "a.txt"
    f.write_bytes(b"abc")
    main([str(f), "--sums"])
    assert capsys.readouterr().out == f"{hashlib.sha256(b'abc').hexdigest()}  {f}\n"


def test_default_output_and_missing_file(tmp_path, capsys):
    f = tmp_path / "a.txt"
    f.write_bytes(b"abc")
    assert main([str(f), "-a", "md5", "-a", "sha1"]) == 0
    out = capsys.readouterr().out
    assert "md5" in out and "sha1" in out and "sha256" not in out
    assert main([str(tmp_path / "missing.txt")]) == 1
