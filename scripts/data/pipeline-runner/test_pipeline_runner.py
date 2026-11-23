import json

import pipeline_runner as pr
import pytest

ORDERS = ("order_id,customer_id,product,qty,price\n1,1,Pen,3,2.5\n2,2,Book,1,10\n3,1,Pen,2,2.5\n"
          "4,3,Lamp,,20\n")
CUSTOMERS = "id,name\n1,Ada\n2,Bob\n"


@pytest.fixture
def work(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "orders.csv").write_text(ORDERS)
    (tmp_path / "customers.csv").write_text(CUSTOMERS)
    return tmp_path


def run(steps, apply=False):
    return pr.run({"steps": steps}, apply)


def result(steps):
    _, columns, rows, _ = run(steps)
    return columns, [[r[c] for c in columns] for r in rows]


def test_read_select_rename_limit(work):
    columns, rows = result([{"read": "orders.csv"}, {"select": ["order_id", "product"]},
                            {"rename": {"product": "item"}}, {"limit": 2}])
    assert columns == ["order_id", "item"] and rows == [["1", "Pen"], ["2", "Book"]]


@pytest.mark.parametrize("flt,expected", [
    ({"column": "qty", "op": ">=", "value": 2}, ["1", "3"]),
    ({"column": "product", "op": "==", "value": "pen"}, []),
    ({"column": "product", "op": "contains", "value": "PEN"}, ["1", "3"]),
    ({"column": "product", "op": "startswith", "value": "b"}, ["2"]),
    ({"column": "product", "op": "matches", "value": "^(Lamp|Book)$"}, ["2", "4"]),
    ({"column": "qty", "op": "is_empty"}, ["4"]),
    ({"column": "qty", "op": "not_empty"}, ["1", "2", "3"]),
    ({"column": "price", "op": "<", "value": 5}, ["1", "3"])])
def test_filter_operators(work, flt, expected):
    _, rows = result([{"read": "orders.csv"}, {"filter": flt}, {"select": ["order_id"]}])
    assert [r[0] for r in rows] == expected


def test_sort_is_numeric_aware_and_supports_desc(work):
    _, rows = result([{"read": "orders.csv"}, {"sort": {"by": "price", "desc": True}},
                      {"select": ["order_id"]}])
    assert [r[0] for r in rows] == ["4", "2", "1", "3"]
    _, rows = result([{"read": "orders.csv"}, {"sort": {"by": ["product", "order_id"]}},
                      {"select": ["order_id"]}])
    assert [r[0] for r in rows] == ["2", "4", "1", "3"]


def test_add_column_expression_template_value_and_blank_inputs(work):
    columns, rows = result([
        {"read": "orders.csv"},
        {"add_column": {"name": "total", "expr": "qty * price + 1"}},
        {"add_column": {"name": "label", "template": "{product}#{order_id}"}},
        {"add_column": {"name": "src", "value": "csv"}},
        {"select": ["total", "label", "src"]}])
    assert rows == [["8.5", "Pen#1", "csv"], ["11", "Book#2", "csv"], ["6", "Pen#3", "csv"],
                    ["", "Lamp#4", "csv"]]


def test_expressions_are_safe():
    with pytest.raises(pr.StepError):
        pr.evaluate("__import__('os').system('x')", {"a": "1"})
    with pytest.raises(pr.StepError):
        pr.evaluate("a ** 2", {"a": "3"})
    with pytest.raises(pr.StepError, match="no column 'zzz'"):
        pr.evaluate("zzz + 1", {"a": "3"})
    assert pr.evaluate("a / 0", {"a": "3"}) == ""
    assert pr.evaluate("-a + 10 // 3", {"a": "2"}) == "1"


def test_dedupe_drop_fill(work):
    _, rows = result([{"read": "orders.csv"}, {"dedupe": ["product"]}, {"select": ["order_id"]}])
    assert [r[0] for r in rows] == ["1", "2", "4"]
    columns, _ = result([{"read": "orders.csv"}, {"drop": ["price", "qty"]}])
    assert columns == ["order_id", "customer_id", "product"]
    _, rows = result([{"read": "orders.csv"}, {"fill": {"column": "qty", "value": 0}},
                      {"select": ["qty"]}])
    assert [r[0] for r in rows] == ["3", "1", "2", "0"]


def test_group_with_aggregates(work):
    columns, rows = result([
        {"read": "orders.csv"},
        {"group": {"by": "product", "agg": {"qty": "sum", "price": "mean"}}},
        {"sort": {"by": "product"}}])
    assert columns == ["product", "qty_sum", "price_mean", "count"]
    assert rows == [["Book", "1", "10", "1"], ["Lamp", "", "20", "1"], ["Pen", "5", "2.5", "2"]]


def test_join_left_and_inner(work):
    columns, rows = result([{"read": "orders.csv"},
                            {"join": {"file": "customers.csv", "on": "customer_id",
                                      "right_on": "id"}}, {"select": ["order_id", "name"]}])
    assert rows == [["1", "Ada"], ["2", "Bob"], ["3", "Ada"], ["4", ""]]
    _, inner = result([{"read": "orders.csv"},
                       {"join": {"file": "customers.csv", "on": "customer_id", "right_on": "id",
                                 "how": "inner"}}])
    assert len(inner) == 3


@pytest.mark.parametrize("steps,fragment", [
    ([], "needs a 'steps' list"),
    ([{"filter": {"column": "x", "value": 1}}], "start the pipeline with a 'read'"),
    ([{"read": "orders.csv"}, {"select": ["nope"]}], "no such column nope"),
    ([{"read": "missing.csv"}], "can't read missing.csv"),
    ([{"read": "orders.csv"}, {"explode": 1}], "unknown step 'explode'"),
    ([{"read": "orders.csv"}, {"limit": "x"}], "'limit' needs a whole number"),
    ([{"read": "orders.csv"}, {"filter": {"column": "qty", "op": "~", "value": 1}}],
     "unknown filter operator"),
    ([{"read": "orders.csv"}, {"group": {"by": "product", "agg": {"qty": "median"}}}],
     "unknown function"),
    ([{"read": "orders.csv", "limit": 1}], "single 'name: settings'")])
def test_errors_name_the_step(work, steps, fragment):
    with pytest.raises(pr.StepError, match=fragment):
        run(steps)


def test_cli_dry_run_apply_and_no_overwrite(work, capsys):
    pipeline = work / "p.yml"
    pipeline.write_text("name: demo\nsteps:\n  - read: orders.csv\n  - filter: {column: qty, "
                        "op: '>=', value: 2}\n  - write: out.csv\n")
    assert pr.main([str(pipeline)]) == 0
    out = capsys.readouterr().out
    assert "Pipeline: demo" in out and "-> 2 row(s), 5 column(s)" in out
    assert "Would write out.csv (2 row(s))" in out and not (work / "out.csv").exists()
    assert pr.main([str(pipeline), "--apply"]) == 0
    header = (work / "out.csv").read_text().splitlines()[0]
    assert header == "order_id,customer_id,product,qty,price"
    assert pr.main([str(pipeline), "--apply"]) == 1
    assert "already exists" in capsys.readouterr().err


def test_cli_json_pipeline_and_bad_files(work, capsys):
    pipeline = work / "p.json"
    pipeline.write_text(json.dumps({"steps": [{"read": "orders.csv"}, {"limit": 1}]}))
    assert pr.main([str(pipeline)]) == 0
    bad = work / "bad.yml"
    bad.write_text("steps: [unclosed")
    assert pr.main([str(bad)]) == 1
    assert "Can't read the pipeline" in capsys.readouterr().err
    missing = work / "m.yml"
    missing.write_text("steps:\n  - read: nope.csv\n")
    assert pr.main([str(missing)]) == 1
    assert "Pipeline stopped: step 1 (read)" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        pr.main([str(work / "none.yml")])
