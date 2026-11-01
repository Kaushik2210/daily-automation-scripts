import json

import pytest
from json_pretty_printer import explain_error, format_json, main


def test_format_and_sort():
    assert format_json('{"b":1,"a":[1,2]}', indent=1, sort_keys=True) == (
        '{\n "a": [\n  1,\n  2\n ],\n "b": 1\n}')


def test_minify_keeps_unicode():
    result = format_json('{ "name" : "café", "n" : [ 1, 2 ] }', minify=True)
    assert result == '{"name":"café","n":[1,2]}'


def test_error_explanation_points_at_column():
    text = '{"a": 1,\n "b": oops}'
    with pytest.raises(json.JSONDecodeError) as caught:
        format_json(text)
    message = explain_error(caught.value, text)
    assert "line 2" in message and message.splitlines()[-1].strip() == "^"


def test_cli_check_and_invalid(tmp_path, capsys):
    good, bad = tmp_path / "g.json", tmp_path / "b.json"
    good.write_text('{"ok": true}')
    bad.write_text("{nope}")
    assert main([str(good), "--check"]) == 0
    assert main([str(bad)]) == 1
    assert "Invalid JSON" in capsys.readouterr().err


def test_output_needs_apply(tmp_path):
    src, out = tmp_path / "in.json", tmp_path / "out.json"
    src.write_text('{"a":1}')
    main([str(src), "-o", str(out)])
    assert not out.exists()
    main([str(src), "-o", str(out), "--apply"])
    assert json.loads(out.read_text()) == {"a": 1}
