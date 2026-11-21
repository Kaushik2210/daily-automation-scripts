import json

import clipboard_history_logger as chl
import pytest


@pytest.mark.parametrize("text,sensitive", [
    ("hello world", False), ("meet at 5pm", False), ("https://example.com/page", False),
    ("password: hunter2", True), ("API_KEY=abc", True),
    ("-----BEGIN RSA PRIVATE KEY-----\nabc", True),
    ("ghp_abcdefghijklmnop1234", True), ("AKIAIOSFODNN7EXAMPLE", True),
    ("4111 1111 1111 1111", True), ("4111 1111 1111 1112", False),
    ("aB3dE5gH7jK9mN1pQ3sT5", True), ("a-normal-hyphenated-sentence-like-text", False),
    ("1234567890", False)])
def test_looks_sensitive(text, sensitive):
    assert chl.looks_sensitive(text) is sensitive


def fake_clipboard(values):
    items = iter(values)
    last = [values[0]]

    def reader():
        last[0] = next(items, last[0])
        return last[0]
    return reader


def run_watch(values, log, **kwargs):
    lines = []
    defaults = {"interval": 0, "seconds": 0, "count": 0, "keep_sensitive": False, "max_chars": 2000}
    defaults.update(kwargs)
    reader = fake_clipboard(values)
    ticks = iter(range(1000))
    result = chl.watch(reader, log, sleep=lambda s: None, clock=lambda: next(ticks),
                       out=lines.append, **defaults)
    return result, lines


def test_watch_logs_changes_only_and_skips_secrets(tmp_path):
    log = tmp_path / "h.jsonl"
    values = ["start", "first copy", "first copy", "", "second copy", "password: x1", "third"]
    (saved, skipped), lines = run_watch(values, log, count=3)
    assert (saved, skipped) == (3, 1)
    entries = chl.load(log)
    assert [e["text"] for e in entries] == ["first copy", "second copy", "third"]
    assert entries[0]["length"] == 10 and any("sensitive" in line for line in lines)


def test_watch_can_keep_sensitive_and_truncate(tmp_path):
    log = tmp_path / "h.jsonl"
    (saved, _), _ = run_watch(["a", "password: " + "x" * 50], log, count=1, keep_sensitive=True,
                              max_chars=20)
    assert saved == 1 and len(chl.load(log)[0]["text"]) == 20 and chl.load(log)[0]["length"] == 60


def test_watch_stops_after_time_limit(tmp_path):
    (saved, _), _ = run_watch(["a", "b", "c", "d", "e", "f"], tmp_path / "h.jsonl", seconds=3)
    assert saved < 6


def test_preview_and_load_ignore_bad_lines(tmp_path):
    assert chl.preview("a\n  b   c") == "a b c" and chl.preview("x" * 100).endswith("…")
    log = tmp_path / "h.jsonl"
    log.write_text('{"time": "2026-11-21T09:00:00", "text": "ok", "length": 2}\nnot json\n')
    assert len(chl.load(log)) == 1 and chl.load(tmp_path / "none") == []


def test_cli_list_and_search(tmp_path, capsys):
    log = tmp_path / "h.jsonl"
    rows = [{"time": f"2026-11-21T09:0{i}:00", "text": text, "length": len(text)}
            for i, text in enumerate(["pip install flask", "meeting notes", "Flask is neat"])]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    assert chl.main(["list", "--log", str(log), "--last", "2"]) == 0
    out = capsys.readouterr().out
    assert "meeting notes" in out and "pip install" not in out and "Showing 2 of 3" in out
    assert chl.main(["search", "flask", "--log", str(log)]) == 0
    out = capsys.readouterr().out
    assert "pip install flask" in out and "Flask is neat" in out and "2 match(es) in 3" in out
    assert chl.main(["search", "zebra", "--log", str(log)]) == 1
    with pytest.raises(SystemExit):
        chl.main(["search", "--log", str(log)])


def test_watch_without_a_clipboard_tool(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(chl, "read_clipboard", lambda: (_ for _ in ()).throw(OSError("none")))
    assert chl.main(["watch", "--log", str(tmp_path / "h.jsonl"), "--count", "1"]) == 1
    assert "Can't read the clipboard" in capsys.readouterr().err
