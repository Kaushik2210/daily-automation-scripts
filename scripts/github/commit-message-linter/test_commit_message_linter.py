import commit_message_linter as cl
import pytest

US = cl.US


def test_good_conventional_subjects():
    assert cl.lint_subject("feat: add login page") == []
    assert cl.lint_subject("fix(cart)!: handle empty cart") == []
    assert cl.lint_subject("docs: update README") == []


def test_bad_subjects_report_reasons():
    assert any("form" in p for p in cl.lint_subject("Fixed the bug"))
    assert any("period" in p for p in cl.lint_subject("fix: stop the crash."))
    assert any("lowercase" in p for p in cl.lint_subject("feat: Add login"))
    assert any("vague" in p for p in cl.lint_subject("wip"))
    assert any("characters" in p for p in cl.lint_subject("feat: " + "x" * 80))
    assert cl.lint_subject("feat: API tweaks") == []   # acronyms may start with capitals


def test_free_style_only_checks_length_and_tidiness():
    assert cl.lint_subject("Add the login page", style="free") == []
    assert cl.lint_subject("Add the login page.", style="free") == ["subject ends with a period"]


def test_parse_subjects():
    text = f"@@abcdef123{US}A{US}a@x{US}2026-01-01{US}feat: one\n10\t2\tf.py\n"
    assert cl.parse_subjects(text) == [("abcdef1", "feat: one")]


def test_cli_exit_codes_and_message_mode(tmp_path, capsys):
    assert cl.main(["--message", "feat: ok message"]) == 0
    assert cl.main(["--message", "Updated stuff."]) == 1
    log = tmp_path / "log.txt"
    log.write_text(f"@@1111111{US}A{US}a@x{US}2026-01-01{US}feat: fine\n"
                   f"@@2222222{US}A{US}a@x{US}2026-01-01{US}wip\n")
    assert cl.main(["--log", str(log)]) == 1
    out = capsys.readouterr().out
    assert "2222222  wip" in out and "2 message(s) checked, 1 with problems." in out
    with pytest.raises(SystemExit):
        cl.main(["--log", str(tmp_path / "missing.txt")])
