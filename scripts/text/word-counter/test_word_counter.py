from word_counter import count_text, main, top_words


def test_count_text():
    c = count_text("hello world\nsecond line\n")
    assert c == {"lines": 2, "words": 4, "chars": 24, "bytes": 24}


def test_bytes_differ_from_chars_for_unicode():
    c = count_text("café")
    assert c["chars"] == 4
    assert c["bytes"] == 5


def test_top_words_ignores_short_words_and_case():
    text = "The cat and the Cat and THE dog"
    assert top_words(text, limit=2) == [("the", 3), ("cat", 2)]


def test_cli_reads_files(tmp_path, capsys):
    f = tmp_path / "a.txt"
    f.write_text("one two three\n")
    main([str(f), "--top", "1"])
    out = capsys.readouterr().out
    assert "a.txt" in out
    assert "Most common words" in out
