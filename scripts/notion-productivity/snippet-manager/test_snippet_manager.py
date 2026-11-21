import json
from datetime import datetime

import pytest
import snippet_manager as sm


def run(tmp_path, *args):
    return sm.main([*args, "--store", str(tmp_path / "s.json")])


def test_fill_placeholders():
    now = datetime(2026, 11, 21, 9, 5)
    assert sm.fill("Hi on {date} at {time} ({datetime})", now) == (
        "Hi on 2026-11-21 at 09:05 (2026-11-21 09:05)")
    assert sm.fill("no placeholders") == "no placeholders"


def test_add_list_show_search(tmp_path, capsys):
    assert run(tmp_path, "add", "sig", "Best regards,\nKaushik") == 0
    assert run(tmp_path, "add", "ty", "Thanks for your message on {date}.") == 0
    data = json.loads((tmp_path / "s.json").read_text())
    assert data["sig"]["text"] == "Best regards,\nKaushik" and data["sig"]["uses"] == 0
    capsys.readouterr()
    assert run(tmp_path, "list") == 0
    out = capsys.readouterr().out
    assert out.index("sig") < out.index("ty") and "2 snippet(s)" in out
    assert run(tmp_path, "show", "ty") == 0
    shown = capsys.readouterr().out
    assert shown.startswith("Thanks for your message on 20") and "{date}" not in shown
    assert run(tmp_path, "search", "regards") == 0
    assert "sig" in capsys.readouterr().out
    assert run(tmp_path, "search", "zebra") == 1


def test_add_refuses_to_replace_without_overwrite(tmp_path, capsys):
    run(tmp_path, "add", "a", "one")
    assert run(tmp_path, "add", "a", "two") == 1
    assert "already exists" in capsys.readouterr().err
    assert run(tmp_path, "add", "a", "two", "--overwrite") == 0
    assert json.loads((tmp_path / "s.json").read_text())["a"]["text"] == "two"


def test_add_from_file(tmp_path):
    source = tmp_path / "t.txt"
    source.write_text("line one\nline two\n")
    assert run(tmp_path, "add", "f", "--file", str(source)) == 0
    assert json.loads((tmp_path / "s.json").read_text())["f"]["text"] == "line one\nline two"


def test_delete_is_a_dry_run_by_default(tmp_path, capsys):
    run(tmp_path, "add", "a", "one")
    assert run(tmp_path, "delete", "a") == 0
    assert "Would delete 'a'" in capsys.readouterr().out and "a" in sm.load(tmp_path / "s.json")
    assert run(tmp_path, "delete", "a", "--apply") == 0
    assert sm.load(tmp_path / "s.json") == {}


def test_unknown_name_suggests_close_matches(tmp_path, capsys):
    run(tmp_path, "add", "email-sig", "x")
    assert run(tmp_path, "show", "sig") == 1
    assert "Did you mean: email-sig" in capsys.readouterr().err


def test_copy_uses_the_clipboard_and_counts_uses(tmp_path, monkeypatch, capsys):
    copied = []
    monkeypatch.setattr(sm, "set_clipboard", copied.append)
    run(tmp_path, "add", "a", "hello")
    assert run(tmp_path, "copy", "a") == 0 and copied == ["hello"]
    assert sm.load(tmp_path / "s.json")["a"]["uses"] == 1
    assert "Copied 'a'" in capsys.readouterr().out


def test_copy_without_a_clipboard_prints_the_text(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sm, "set_clipboard", lambda text: (_ for _ in ()).throw(OSError("none")))
    run(tmp_path, "add", "a", "hello")
    capsys.readouterr()
    assert run(tmp_path, "copy", "a") == 1
    captured = capsys.readouterr()
    assert "hello" in captured.out and "Couldn't use the clipboard" in captured.err


def test_bad_store_and_missing_arguments(tmp_path, capsys):
    (tmp_path / "s.json").write_text("[1, 2]")
    assert run(tmp_path, "list") == 1
    assert "Can't read" in capsys.readouterr().err
    (tmp_path / "s.json").unlink()
    with pytest.raises(SystemExit):
        run(tmp_path, "show")
    with pytest.raises(SystemExit):
        run(tmp_path, "add", "x")
