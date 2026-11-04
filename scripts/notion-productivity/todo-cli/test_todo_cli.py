import pytest
import todo_cli as td


def fresh():
    return {"next_id": 1, "todos": []}


def test_add_assigns_incrementing_ids():
    data = fresh()
    a = td.add_todo(data, "first", "low")
    b = td.add_todo(data, "second")
    assert (a["id"], b["id"], data["next_id"]) == (1, 2, 3)


def test_sorting_priority_then_id_and_done_hidden():
    data = fresh()
    td.add_todo(data, "low one", "low")
    td.add_todo(data, "high one", "high")
    td.add_todo(data, "normal one")
    td.find(data, 3)["done"] = True
    assert [t["text"] for t in td.sorted_todos(data)] == ["high one", "low one"]
    assert [t["text"] for t in td.sorted_todos(data, show_done=True)][-1] == "normal one"


def test_render_marks_done_and_high_priority():
    data = fresh()
    td.add_todo(data, "urgent", "high")
    td.add_todo(data, "finished")
    td.find(data, 2)["done"] = True
    assert td.render(td.sorted_todos(data, True)) == ["[ ]   1 ! urgent", "[x]   2   finished"]


def test_cli_round_trip(tmp_path, capsys):
    f = str(tmp_path / "t.json")
    td.main(["add", "Write", "report", "-p", "high", "--file", f])
    td.main(["add", "Call Sam", "--file", f])
    td.main(["done", "2", "--file", f])
    capsys.readouterr()
    td.main(["list", "--file", f])
    out = capsys.readouterr().out
    assert "Write report" in out and "Call Sam" not in out and "1 open, 1 done." in out
    td.main(["clear-done", "--file", f])
    assert "Removed 1 finished" in capsys.readouterr().out
    td.main(["remove", "1", "--file", f])
    td.main(["list", "--file", f])
    assert "Nothing to do!" in capsys.readouterr().out


def test_errors(tmp_path, capsys):
    f = str(tmp_path / "t.json")
    assert td.main(["done", "9", "--file", f]) == 1
    assert "No task #9" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        td.main(["add", "--file", f])
    with pytest.raises(SystemExit):
        td.main(["done", "abc", "--file", f])
