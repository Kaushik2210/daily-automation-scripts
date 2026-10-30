from whitespace_stripper import clean_text, collect_files, main


def test_strips_trailing_whitespace_and_blank_tail():
    assert clean_text("a  \nb\t\n\n\n") == "a\nb\n"


def test_keeps_crlf_when_file_uses_it():
    assert clean_text("a \r\nb\r\n") == "a\r\nb\r\n"
    assert clean_text("a\r\nb\n", eol="lf") == "a\nb\n"
    assert clean_text("a\nb\n", eol="crlf") == "a\r\nb\r\n"


def test_final_newline_option():
    assert clean_text("a\nb", final_newline=False) == "a\nb"
    assert clean_text("a\nb") == "a\nb\n"
    assert clean_text("   \n") == ""


def test_collect_files_matches_pattern(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.py").write_text("x")
    names = [p.name for p in collect_files([tmp_path], "*.txt")]
    assert names == ["a.txt"]


def test_dry_run_then_apply(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"hello  \nworld\n")
    main([str(f)])
    assert f.read_bytes() == b"hello  \nworld\n"
    main([str(f), "--apply"])
    assert f.read_bytes() == b"hello\nworld\n"
