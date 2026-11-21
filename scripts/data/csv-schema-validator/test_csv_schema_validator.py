import json

import csv_schema_validator as csv_v
import pytest

SCHEMA = {"strict": True, "columns": {
    "id": {"type": "int", "required": True, "unique": True, "min": 1},
    "email": {"type": "str", "pattern": r"^[^@\s]+@[^@\s]+$"},
    "age": {"type": "int", "min": 0, "max": 120},
    "status": {"type": "str", "allowed": ["active", "inactive"]},
    "joined": {"type": "date", "format": "%Y-%m-%d"},
    "score": {"type": "float", "min": 0, "max": 100},
    "vip": {"type": "bool"}}}
HEADER = ["id", "email", "age", "status", "joined", "score", "vip"]


def run(rows, schema=SCHEMA, header=HEADER):
    numbered = [(i + 2, row) for i, row in enumerate(rows)]
    return csv_v.validate(numbered, header, schema)


def test_clean_rows_pass():
    errors, structure = run([["1", "a@b.co", "30", "active", "2024-01-31", "88.5", "yes"],
                             ["2", "", "", "", "", "", ""]])
    assert errors == [] and structure == []


@pytest.mark.parametrize("row,column,fragment", [
    (["x", "a@b", "1", "active", "2024-01-01", "1", "no"], "id", "not a valid int"),
    (["0", "a@b", "1", "active", "2024-01-01", "1", "no"], "id", "below the minimum of 1"),
    (["1", "nope", "1", "active", "2024-01-01", "1", "no"], "email", "does not match the pattern"),
    (["1", "a@b", "150", "active", "2024-01-01", "1", "no"], "age", "above the maximum of 120"),
    (["1", "a@b", "1", "pending", "2024-01-01", "1", "no"], "status", "is not one of"),
    (["1", "a@b", "1", "active", "12/31/2024", "1", "no"], "joined", "expected format %Y-%m-%d"),
    (["1", "a@b", "1", "active", "2024-02-30", "1", "no"], "joined", "not a valid date"),
    (["1", "a@b", "1", "active", "2024-01-01", "n/a", "no"], "score", "not a valid float"),
    (["1", "a@b", "1", "active", "2024-01-01", "1", "maybe"], "vip", "not a valid bool")])
def test_cell_problems(row, column, fragment):
    errors, _ = run([row])
    assert len(errors) == 1 and errors[0][1] == column and fragment in errors[0][3]
    assert errors[0][0] == 2


def test_required_unique_and_row_length():
    errors, _ = run([["", "a@b", "", "", "", "", ""], ["5", "", "", "", "", "", ""],
                     ["5", "", "", "", "", "", ""], ["9", "a@b"]])
    kinds = [(line, col, problem) for line, col, _, problem in errors]
    assert (2, "id", "is required but empty") in kinds
    assert (4, "id", "is a duplicate (first seen on line 3)") in kinds
    assert (5, "(row)", "has 2 fields, expected 7") in kinds


def test_structure_checks():
    _, structure = csv_v.validate([], ["id", "extra", "id"], SCHEMA)
    assert "missing column 'email'" in structure and "unexpected column 'extra'" in structure
    assert "duplicate column names in the header" in structure
    _, relaxed = csv_v.validate([], ["id"], {"columns": {"id": {}}})
    assert relaxed == []


def test_infer_column():
    assert csv_v.infer_column(["1", "20", "3"]) == {"type": "int", "min": 1, "max": 20}
    assert csv_v.infer_column(["1.5", "2"]) == {"type": "float", "min": 1.5, "max": 2.0}
    assert csv_v.infer_column(["yes", "no"]) == {"type": "bool"}
    assert csv_v.infer_column(["2024-01-05", "2023-12-31"])["type"] == "date"
    assert csv_v.infer_column(["a", "b", "a", "b", "a", "b"])["allowed"] == ["a", "b"]
    assert csv_v.infer_column(["hello", "world"]) == {"type": "str"}
    assert csv_v.infer_column([]) == {"type": "str"}


def test_cli_validate_infer_and_errors(tmp_path, capsys):
    data = tmp_path / "d.csv"
    data.write_text("id,email,age,status,joined,score,vip\n1,a@b.co,30,active,2024-01-31,5,yes\n"
                    "1,bad,200,active,2024-01-31,5,yes\n")
    schema = tmp_path / "s.json"
    schema.write_text(json.dumps(SCHEMA))
    assert csv_v.main([str(data), str(schema)]) == 1
    out = capsys.readouterr().out
    assert "line 3" in out and "is a duplicate" in out and "3 problem(s) on 1 row(s)" in out
    assert csv_v.main([str(data), str(schema), "--max-errors", "1"]) == 1
    assert "... and 2 more" in capsys.readouterr().out
    assert csv_v.main([str(data), "--infer"]) == 0
    inferred = json.loads(capsys.readouterr().out)
    assert inferred["columns"]["age"]["type"] == "int" and inferred["strict"] is True
    assert csv_v.main([str(data), str(tmp_path / "none.json")]) == 1
    with pytest.raises(SystemExit):
        csv_v.main([str(data)])


def test_empty_file(tmp_path, capsys):
    empty = tmp_path / "e.csv"
    empty.write_text("")
    assert csv_v.main([str(empty), "--infer"]) == 1
    assert "empty" in capsys.readouterr().err
