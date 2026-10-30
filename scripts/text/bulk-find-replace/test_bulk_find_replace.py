from bulk_find_replace import main, replace_text


def test_plain_replace_is_literal():
    assert replace_text("a.b a.b", "a.b", "X") == ("X X", 2)
    assert replace_text("axb", "a.b", "X") == ("axb", 0)


def test_ignore_case_and_regex_groups():
    assert replace_text("Hello hello", "hello", "bye", ignore_case=True) == ("bye bye", 2)
    assert replace_text("v1.2", r"v(\d)\.(\d)", r"\2-\1", use_regex=True) == ("2-1", 1)


def test_replacement_backslashes_are_literal_in_plain_mode():
    assert replace_text("a", "a", r"\1") == (r"\1", 1)


def test_dry_run_then_apply(tmp_path, capsys):
    f = tmp_path / "a.txt"
    f.write_text("old name, old name")
    (tmp_path / "bin.dat").write_bytes(b"\xff\xfe\x00old")
    main([str(tmp_path), "--find", "old", "--replace", "new"])
    assert f.read_text() == "old name, old name"
    assert "2 occurrence(s) in 1 file(s)" in capsys.readouterr().out
    main([str(tmp_path), "--find", "old", "--replace", "new", "--apply"])
    assert f.read_text() == "new name, new name"
