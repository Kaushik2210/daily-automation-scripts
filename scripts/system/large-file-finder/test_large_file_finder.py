import pytest
from large_file_finder import find_large, main, parse_size


def test_parse_size():
    assert parse_size("500") == 500
    assert parse_size("10KB") == 10 * 1024
    assert parse_size("1.5 gb") == int(1.5 * 1024**3)
    with pytest.raises(ValueError):
        parse_size("lots")
    with pytest.raises(ValueError):
        parse_size("10XB")


def test_biggest_first_and_top_limit(tmp_path):
    for name, size in (("a", 10), ("b", 300), ("c", 50)):
        (tmp_path / name).write_bytes(b"x" * size)
    found = find_large(tmp_path, top=2)
    assert [s for s, _, _ in found] == [300, 50]


def test_min_size_and_exclude(tmp_path):
    (tmp_path / "skipme").mkdir()
    (tmp_path / "skipme" / "huge.bin").write_bytes(b"x" * 1000)
    (tmp_path / "small.txt").write_bytes(b"x" * 5)
    (tmp_path / "ok.bin").write_bytes(b"x" * 200)
    found = find_large(tmp_path, min_size=100, exclude=["skipme"])
    assert [p.rsplit("ok.bin")[-1] for _, _, p in found] == [""]


def test_cli_output(tmp_path, capsys):
    (tmp_path / "f.bin").write_bytes(b"x" * 2048)
    main([str(tmp_path), "--min-size", "1KB"])
    out = capsys.readouterr().out
    assert "2.0 KB" in out and "1 file(s) listed" in out
