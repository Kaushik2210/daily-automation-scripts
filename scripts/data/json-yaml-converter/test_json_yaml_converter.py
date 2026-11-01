import json

from json_yaml_converter import convert, detect_format, main


def test_detect_format(tmp_path):
    assert detect_format(tmp_path / "a.yml") == "yaml"
    assert detect_format(tmp_path / "a.YAML") == "yaml"
    assert detect_format(tmp_path / "a.json") == "json"


def test_json_to_yaml_keeps_key_order():
    out = convert('{"name": "Ada", "tags": ["a", "b"], "n": 1}', "json", "yaml")
    assert out.splitlines()[0] == "name: Ada"
    assert "- a" in out and "n: 1" in out


def test_yaml_to_json_round_trip():
    text = "name: Ada\nskills:\n  - math\n  - code\nactive: true\n"
    data = json.loads(convert(text, "yaml", "json"))
    assert data == {"name": "Ada", "skills": ["math", "code"], "active": True}


def test_cli_invalid_input_and_apply(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{oops")
    assert main([str(bad)]) == 1
    assert "Couldn't read" in capsys.readouterr().err
    src, out = tmp_path / "a.yaml", tmp_path / "a.json"
    src.write_text("x: 1\n")
    main([str(src), "-o", str(out)])
    assert not out.exists()
    main([str(src), "-o", str(out), "--apply"])
    assert json.loads(out.read_text()) == {"x": 1}
