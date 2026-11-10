import json
from datetime import date

import pytest
import reading_list_manager as rlm

TODAY = date(2026, 11, 10)


def make(tmp_path, books=None):
    path = tmp_path / "list.json"
    if books is not None:
        path.write_text(json.dumps({"next_id": len(books) + 1, "books": books}))
    return path


def book(n, title, status="to-read", rating=None, finished=None, author="A. Writer"):
    return {"id": n, "title": title, "author": author, "status": status, "rating": rating,
            "added": "2026-01-01", "finished": finished}


def test_load_missing_file_and_repairs_missing_keys(tmp_path):
    assert rlm.load(tmp_path / "none.json") == {"next_id": 1, "books": []}
    path = tmp_path / "old.json"
    path.write_text(json.dumps({"books": [book(7, "X")]}))
    assert rlm.load(path)["next_id"] == 8


def test_add_book_numbers_and_rejects_duplicates():
    data = {"next_id": 1, "books": []}
    first = rlm.add_book(data, "Deep Work", "Cal Newport", TODAY)
    assert first["id"] == 1 and first["status"] == "to-read" and first["added"] == "2026-11-10"
    assert rlm.add_book(data, "deep work") is None
    assert rlm.add_book(data, "Another")["id"] == 2


def test_listing_groups_by_status_and_hides_others():
    data = {"books": [book(1, "A", "done", 5, "2026-02-01"), book(2, "B", "reading"),
                      book(3, "C"), book(4, "D", "done", None, "2026-03-01")]}
    lines = rlm.listing(data)
    assert lines[0] == "READING (1)" and "  B - A. Writer" in lines[1].replace("  2  ", "  ")
    assert lines.index("DONE (2)") > lines.index("TO-READ (1)")
    done_titles = [line.split()[1] for line in lines[lines.index("DONE (2)") + 1:] if line]
    assert done_titles == ["D", "A"]  # most recently finished first
    only_waiting = rlm.listing(data, "to-read")
    assert only_waiting[0] == "TO-READ (1)" and len(only_waiting) == 3


def test_stats_summary():
    data = {"books": [book(1, "A", "done", 5, "2026-02-01"), book(2, "B", "done", 3, "2026-02-20"),
                      book(3, "C", "reading"), book(4, "D")]}
    lines = rlm.stats(data)
    assert lines[0] == "4 book(s): 2 finished, 1 reading, 1 waiting."
    assert "Average rating: 4.0/5 over 2 rated book(s)." in lines
    assert "Finished by month: 2026-02 (2)" in lines and "Top rated: A" in lines
    assert rlm.stats({"books": [book(1, "A")]}) == ["1 book(s): 0 finished, 0 reading, 1 waiting."]


def run(tmp_path, *args):
    return rlm.main([*args, "--file", str(tmp_path / "list.json"), "--today", "2026-11-10"])


def test_full_workflow_through_the_cli(tmp_path, capsys):
    assert run(tmp_path, "add", "Deep", "Work", "--author", "Cal Newport") == 0
    assert run(tmp_path, "add", "Atomic Habits") == 0
    assert run(tmp_path, "start", "1") == 0
    assert run(tmp_path, "finish", "1", "--rating", "5") == 0
    assert run(tmp_path, "rate", "2", "--rating", "4") == 0
    capsys.readouterr()
    assert run(tmp_path, "list") == 0
    out = capsys.readouterr().out
    assert "TO-READ (1)" in out and "DONE (1)" in out and "[5/5]" in out and "[4/5]" in out
    saved = json.loads((tmp_path / "list.json").read_text())
    assert saved["books"][0]["finished"] == "2026-11-10"
    assert run(tmp_path, "remove", "2") == 0
    assert [b["id"] for b in json.loads((tmp_path / "list.json").read_text())["books"]] == [1]


def test_cli_errors(tmp_path, capsys):
    make(tmp_path, [book(1, "Only")])
    assert run(tmp_path, "add", "only") == 1
    assert "already on the list" in capsys.readouterr().err
    assert run(tmp_path, "finish", "9") == 1
    assert "No book #9" in capsys.readouterr().err
    bad_calls = (["add"], ["start"], ["start", "x"], ["rate", "1"],
                 ["finish", "1", "--rating", "9"])
    for args in bad_calls:
        with pytest.raises(SystemExit):
            run(tmp_path, *args)
    (tmp_path / "list.json").write_text("{broken")
    assert run(tmp_path, "list") == 1


def test_empty_list_messages(tmp_path, capsys):
    assert run(tmp_path, "list") == 0 and run(tmp_path, "stats") == 0
    out = capsys.readouterr().out
    assert "Nothing on the list yet." in out and "The list is empty." in out
    assert not (tmp_path / "list.json").exists()  # reading never creates the file
