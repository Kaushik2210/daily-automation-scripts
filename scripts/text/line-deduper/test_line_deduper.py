from line_deduper import dedupe_lines, main


def test_keeps_first_occurrence_in_order():
    assert dedupe_lines(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]


def test_ignore_case():
    assert dedupe_lines(["Apple", "apple", "Pear"], ignore_case=True) == ["Apple", "Pear"]


def test_strip_whitespace():
    assert dedupe_lines(["x", " x ", "y"], strip=True) == ["x", "y"]
    assert dedupe_lines(["x", " x "]) == ["x", " x "]


def test_cli_output_file(tmp_path):
    src = tmp_path / "in.txt"
    out = tmp_path / "out.txt"
    src.write_text("one\ntwo\none\n")
    main([str(src), "-o", str(out)])
    assert out.read_text() == "one\ntwo\n"
    assert src.read_text() == "one\ntwo\none\n"
