import json

import json_schema_validator as jsv
import pytest


def problems(value, schema):
    return jsv.validate(value, schema)


@pytest.mark.parametrize("value,kind,ok", [
    (3, "integer", True), (3.0, "integer", True), (3.5, "integer", False), (True, "integer", False),
    (True, "number", False), (2.5, "number", True), ("a", "string", True), (1, "string", False),
    (None, "null", True), ([], "array", True), ({}, "object", True), (True, "boolean", True)])
def test_type_checks(value, kind, ok):
    assert (problems(value, {"type": kind}) == []) is ok


def test_type_error_message_and_union_types():
    assert problems("x", {"type": "integer"}) == [("$", "is string, expected integer")]
    assert problems(None, {"type": ["string", "null"]}) == []


def test_string_rules():
    schema = {"type": "string", "minLength": 2, "maxLength": 4, "pattern": "^[a-z]+$"}
    assert problems("abc", schema) == []
    assert [m for _, m in problems("A", schema)] == [
        "is shorter than 2 character(s)", "does not match the pattern ^[a-z]+$"]
    assert "is longer than 4" in problems("abcdef", schema)[0][1]


@pytest.mark.parametrize("value,fmt,ok", [
    ("a@b.com", "email", True), ("nope", "email", False), ("2024-02-29", "date", True),
    ("2024-02-30", "date", False), ("2024-01-01T10:00:00Z", "date-time", True),
    ("10.0.0.256", "ipv4", False), ("192.168.1.1", "ipv4", True),
    ("https://x.org/a", "uri", True), ("x", "uri", False), ("x", "unknown-format", True)])
def test_formats(value, fmt, ok):
    assert (problems(value, {"format": fmt}) == []) is ok


def test_number_rules():
    schema = {"minimum": 0, "maximum": 10, "multipleOf": 0.5, "exclusiveMinimum": -1}
    assert problems(5, schema) == [] and problems(2.5, schema) == []
    assert [m for _, m in problems(11, schema)] == ["is above the maximum of 10"]
    assert "is not a multiple of 0.5" in [m for _, m in problems(2.3, schema)]
    assert problems(0, {"exclusiveMinimum": 0}) == [("$", "must be greater than 0")]


def test_object_required_additional_and_nested_paths():
    schema = {"type": "object", "required": ["a"], "additionalProperties": False,
              "properties": {"a": {"type": "integer"}, "b": {"type": "object", "properties": {
                  "c": {"type": "string"}}}}}
    assert problems({"a": 1, "b": {"c": "x"}}, schema) == []
    found = dict(problems({"b": {"c": 5}, "z": 1}, schema))
    assert found == {"$": "is missing the required property 'a'",
                     "$.b.c": "is integer, expected string", "$.z": "is not an allowed property"}


def test_additional_properties_schema_and_pattern_properties():
    schema = {"patternProperties": {"^x_": {"type": "integer"}},
              "additionalProperties": {"type": "string"}}
    assert problems({"x_1": 1, "other": "s"}, schema) == []
    found = dict(problems({"x_1": "no", "other": 2}, schema))
    assert set(found) == {"$.x_1", "$.other"}


def test_arrays():
    schema = {"type": "array", "items": {"type": "integer"}, "minItems": 1, "maxItems": 3,
              "uniqueItems": True}
    assert problems([1, 2], schema) == []
    assert dict(problems([1, 1, "x"], schema)) == {
        "$[1]": "is a duplicate of an earlier item", "$[2]": "is string, expected integer"}
    assert "fewer than 1" in problems([], schema)[0][1]
    tuple_schema = {"items": [{"type": "string"}, {"type": "integer"}]}
    assert dict(problems(["a", "b"], tuple_schema)) == {"$[1]": "is string, expected integer"}


def test_enum_const_and_combinators():
    assert problems("x", {"enum": ["a", "b"]}) == [("$", 'must be one of "a", "b"')]
    assert problems(2, {"const": 1}) == [("$", "must equal 1")]
    assert problems(5, {"anyOf": [{"type": "string"}, {"type": "integer"}]}) == []
    assert "anyOf" in problems(5.5, {"anyOf": [{"type": "string"}, {"type": "integer"}]})[0][1]
    assert "matches 2 of the oneOf" in problems(1, {"oneOf": [{"type": "integer"},
                                                              {"minimum": 0}]})[0][1]
    assert problems("a", {"not": {"type": "integer"}}) == []
    assert problems(1, {"not": {"type": "integer"}})
    assert len(problems(1, {"allOf": [{"minimum": 5}, {"maximum": 0}]})) == 2


def test_if_then_else():
    schema = {"if": {"properties": {"kind": {"const": "a"}}, "required": ["kind"]},
              "then": {"required": ["x"]}, "else": {"required": ["y"]}}
    assert problems({"kind": "a", "x": 1}, schema) == []
    assert problems({"kind": "a"}, schema)[0][1] == "is missing the required property 'x'"
    assert problems({"kind": "b"}, schema)[0][1] == "is missing the required property 'y'"


def test_refs():
    schema = {"definitions": {"pos": {"type": "integer", "minimum": 1}},
              "properties": {"n": {"$ref": "#/definitions/pos"}}}
    assert problems({"n": 2}, schema) == []
    assert problems({"n": 0}, schema) == [("$.n", "is below the minimum of 1")]
    with pytest.raises(ValueError):
        problems({"n": 2}, {"$ref": "http://elsewhere/schema"})
    with pytest.raises(ValueError):
        problems({"n": 2}, {"$ref": "#/definitions/missing"})


def test_boolean_schemas():
    assert problems(1, True) == [] and problems(1, False) == [("$", "no value is allowed here")]


def test_cli_files_and_folders(tmp_path, capsys):
    schema = tmp_path / "s.json"
    schema.write_text(json.dumps({"type": "object", "required": ["a"],
                                  "properties": {"a": {"type": "integer"}}}))
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "good.json").write_text('{"a": 1}')
    (docs / "bad.json").write_text('{"a": "x"}')
    (docs / "broken.json").write_text("{not json")
    assert jsv.main([str(schema), str(docs)]) == 1
    out = capsys.readouterr().out
    assert "good.json: valid" in out and "bad.json: 1 problem(s)" in out
    assert "$.a is string, expected integer" in out and "broken.json: can't be read" in out
    assert "1 of 3 file(s) valid." in out
    assert jsv.main([str(schema), str(docs / "good.json")]) == 0
    assert jsv.main([str(tmp_path / "none.json"), str(docs)]) == 1
    empty = tmp_path / "empty"
    empty.mkdir()
    assert jsv.main([str(schema), str(empty)]) == 1
