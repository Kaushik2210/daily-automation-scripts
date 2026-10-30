from text_diff_viewer import colorize, main, make_diff, similarity


def test_make_diff_marks_changes():
    diff = make_diff("a\nb\nc", "a\nB\nc", "x", "y")
    assert diff[0] == "--- x" and diff[1] == "+++ y"
    assert "-b" in diff and "+B" in diff


def test_identical_text_has_no_diff():
    assert make_diff("same\n", "same\n") == []
    assert similarity("same", "same") == 1.0


def test_colorize_adds_and_removes():
    assert colorize("+new").startswith("\033[32m")
    assert colorize("-old").startswith("\033[31m")
    assert colorize(" context") == " context"


def test_cli_exit_codes(tmp_path, capsys):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text("one\ntwo\n")
    b.write_text("one\n2\n")
    assert main([str(a), str(b)]) == 0
    assert "+2" in capsys.readouterr().out
    assert main([str(a), str(b), "--exit-code"]) == 1
    b.write_text("one\ntwo\n")
    assert main([str(a), str(b), "--exit-code"]) == 0
