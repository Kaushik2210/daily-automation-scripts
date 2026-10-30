from extension_counter import count_extensions, main


def test_counts_and_sizes(tmp_path):
    (tmp_path / "a.TXT").write_text("abc")
    (tmp_path / "b.txt").write_text("de")
    (tmp_path / "c.py").write_text("x")
    stats = count_extensions(tmp_path)
    assert stats[".txt"] == [2, 5]
    assert stats[".py"] == [1, 1]


def test_no_extension_bucket(tmp_path):
    (tmp_path / "Makefile").write_text("x")
    assert "(none)" in count_extensions(tmp_path)


def test_nested_files_counted(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.md").write_text("x")
    assert count_extensions(tmp_path)[".md"][0] == 1


def test_cli_top_and_summary(tmp_path, capsys):
    for name in ("a.txt", "b.txt", "c.py", "d.md"):
        (tmp_path / name).write_text("x")
    main([str(tmp_path), "--top", "1"])
    out = capsys.readouterr().out
    assert ".txt" in out
    assert "4 file(s), 3 extension(s)" in out
