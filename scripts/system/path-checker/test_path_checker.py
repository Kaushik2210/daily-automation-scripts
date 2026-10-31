import os

from path_checker import analyze, cleaned, main


def test_finds_missing_empty_duplicate_and_file(tmp_path):
    good = tmp_path / "bin"
    good.mkdir()
    a_file = tmp_path / "file.txt"
    a_file.write_text("x")
    entries = [str(good), "", str(tmp_path / "gone"), str(good), str(a_file)]
    result = analyze(entries)
    kinds = [(pos, problem) for pos, _, problem in result]
    assert (2, "empty") in kinds
    assert (3, "missing") in kinds
    assert (4, "duplicate of #1") in kinds
    assert (5, "not a folder") in kinds


def test_cleaned_keeps_order_and_drops_bad(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    entries = [str(b), str(tmp_path / "nope"), str(a), str(b), ""]
    assert cleaned(entries) == [str(b), str(a)]


def test_clean_path_exits_zero(tmp_path, capsys):
    folder = tmp_path / "bin"
    folder.mkdir()
    assert main(["--path", str(folder)]) == 0
    assert "0 problem(s)" in capsys.readouterr().out


def test_cli_suggest(tmp_path, capsys):
    folder = tmp_path / "bin"
    folder.mkdir()
    value = os.pathsep.join([str(folder), str(tmp_path / "gone")])
    assert main(["--path", value, "--suggest"]) == 1
    out = capsys.readouterr().out
    assert "missing" in out and f"Cleaned PATH:\n{folder}" in out
