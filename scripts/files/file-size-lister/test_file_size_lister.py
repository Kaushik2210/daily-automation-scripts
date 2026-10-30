from file_size_lister import human_size, list_sizes, main


def test_human_size():
    assert human_size(512) == "512 B"
    assert human_size(2048) == "2.0 KB"
    assert human_size(5 * 1024 * 1024) == "5.0 MB"


def test_sorted_largest_first(tmp_path):
    (tmp_path / "small.txt").write_text("a")
    (tmp_path / "big.txt").write_text("a" * 100)
    names = [path.name for _, path in list_sizes(tmp_path)]
    assert names == ["big.txt", "small.txt"]


def test_recursive_flag(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.txt").write_text("abc")
    assert list_sizes(tmp_path) == []
    assert len(list_sizes(tmp_path, recursive=True)) == 1


def test_top_limit(tmp_path, capsys):
    for i in range(5):
        (tmp_path / f"f{i}.txt").write_text("x" * (i + 1))
    main([str(tmp_path), "--top", "2"])
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 3
    assert "5 file(s)" in out[-1]
