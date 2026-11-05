import gitignore_generator as gi
import pytest


def test_generate_blocks_in_order_without_repeats():
    text = gi.generate(["python", "node"])
    assert text.startswith("# python\n__pycache__/")
    assert "\n\n# node\n" in text
    assert text.count("dist/") == 1 and text.count("build/") == 1   # shared lines appear once


def test_every_template_is_non_empty_and_clean():
    for name, lines in gi.TEMPLATES.items():
        assert lines and all(line == line.strip() for line in lines), name


def test_missing_lines():
    assert gi.missing_lines("a\nb\n", "a\nc\n\nb\n") == ["c"]


def test_cli_preview_write_and_no_overwrite(tmp_path, capsys):
    out = tmp_path / ".gitignore"
    gi.main(["python", "-o", str(out)])
    assert not out.exists() and "__pycache__/" in capsys.readouterr().out
    assert gi.main(["python", "-o", str(out), "--apply"]) == 0
    assert gi.main(["python", "-o", str(out), "--apply"]) == 1
    capsys.readouterr()


def test_append_adds_only_new_lines(tmp_path, capsys):
    out = tmp_path / ".gitignore"
    out.write_text("__pycache__/\nmy-own-rule\n")
    assert gi.main(["python", "-o", str(out), "--append", "--apply"]) == 0
    result = out.read_text()
    assert result.count("__pycache__/") == 1 and "my-own-rule" in result and ".venv/" in result
    assert "Appended" in capsys.readouterr().out


def test_unknown_stack_rejected():
    with pytest.raises(SystemExit):
        gi.main(["cobol"])
