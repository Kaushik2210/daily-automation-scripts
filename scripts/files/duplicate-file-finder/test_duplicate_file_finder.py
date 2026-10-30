from duplicate_file_finder import find_duplicates, main


def test_finds_identical_files(tmp_path):
    (tmp_path / "a.txt").write_text("same")
    (tmp_path / "b.txt").write_text("same")
    (tmp_path / "c.txt").write_text("diff")
    groups = find_duplicates(tmp_path)
    assert len(groups) == 1
    assert {p.name for p in groups[0]} == {"a.txt", "b.txt"}


def test_same_size_different_content_is_not_duplicate(tmp_path):
    (tmp_path / "a.txt").write_text("abcd")
    (tmp_path / "b.txt").write_text("abce")
    assert find_duplicates(tmp_path) == []


def test_min_size_filters_small_files(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.txt").write_text("x")
    assert find_duplicates(tmp_path, min_size=10) == []


def test_nested_duplicates_and_report(tmp_path, capsys):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "sub" / "a copy.txt").write_text("hello")
    main([str(tmp_path)])
    assert "1 duplicate group(s)" in capsys.readouterr().out
