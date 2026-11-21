from datetime import datetime

import pytest
import text_expander as te

MAP = {"btw": "by the way", "omw": "on my way", ";sig": "Best,\nKaushik", ";date": "{date}",
       "addr": "12 Park Street"}


def test_load_map_text_and_json(tmp_path):
    path = tmp_path / "map.txt"
    path.write_text("# comment\n\nbtw = by the way\n;sig = Best,\\nKaushik\neq = a = b\n")
    assert te.load_map(path) == {"btw": "by the way", ";sig": "Best,\nKaushik", "eq": "a = b"}
    js = tmp_path / "map.json"
    js.write_text('{"omw": "on my way", "n": 5}')
    assert te.load_map(js) == {"omw": "on my way", "n": "5"}


@pytest.mark.parametrize("content,message", [("just words\n", "line 1"),
                                             (" = nothing\n", "line 1")])
def test_load_map_errors(tmp_path, content, message):
    path = tmp_path / "m.txt"
    path.write_text(content)
    with pytest.raises(ValueError, match=message):
        te.load_map(path)
    arr = tmp_path / "m.json"
    arr.write_text("[1]")
    with pytest.raises(ValueError):
        te.load_map(arr)


def test_whole_words_only():
    text, counts = te.expand("btw the abtwx and btw. omw!", MAP)
    assert text == "by the way the abtwx and by the way. on my way!"
    assert counts == {"btw": 2, "omw": 1}


def test_symbol_abbreviations_and_newlines():
    text, counts = te.expand("Hi\n;sig and ;sig2", MAP)
    assert text == "Hi\nBest,\nKaushik and ;sig2" and counts == {";sig": 1}


def test_longest_abbreviation_wins():
    text, _ = te.expand("addr1 addr", {"addr": "A", "addr1": "B"})
    assert text == "B A"


def test_case_handling():
    assert te.expand("BTW btw", MAP)[0] == "BTW by the way"
    text, counts = te.expand("BTW btw", MAP, ignore_case=True)
    assert text == "by the way by the way" and counts == {"btw": 2}


def test_placeholders_and_empty_map():
    now = datetime(2026, 11, 21, 9, 5)
    assert te.expand("on ;date", MAP, now=now)[0] == "on 2026-11-21"
    assert te.expand("anything", {}) == ("anything", {})
    assert te.fill("{datetime}/{time}", now) == "2026-11-21 09:05/09:05"


def test_cli_dry_run_then_apply_with_backup(tmp_path, capsys):
    mapping = tmp_path / "map.txt"
    mapping.write_text("btw = by the way\nomw = on my way\n")
    doc = tmp_path / "note.txt"
    doc.write_text("Hi,\nbtw I am omw.\n")
    other = tmp_path / "other.txt"
    other.write_text("nothing here\n")
    assert te.main([str(doc), str(other), "--map", str(mapping)]) == 0
    out = capsys.readouterr().out
    assert "note.txt: 2 replacement(s) (btw x1, omw x1)" in out
    assert "- btw I am omw." in out and "+ by the way I am on my way." in out
    assert "other.txt: nothing to expand" in out and doc.read_text() == "Hi,\nbtw I am omw.\n"
    assert te.main([str(doc), "--map", str(mapping), "--apply"]) == 0
    assert doc.read_text() == "Hi,\nby the way I am on my way.\n"
    assert (tmp_path / "note.txt.bak").read_text() == "Hi,\nbtw I am omw.\n"
    doc.write_text("btw again\n")
    assert te.main([str(doc), "--map", str(mapping), "--apply"]) == 0
    assert len(list(tmp_path.glob("note.txt*.bak"))) == 2  # the first backup was not overwritten


def test_bad_map(tmp_path, capsys):
    assert te.main([str(tmp_path / "a.txt"), "--map", str(tmp_path / "none.txt")]) == 1
    assert "Can't read the map" in capsys.readouterr().err
    empty = tmp_path / "e.txt"
    empty.write_text("# nothing\n")
    assert te.main([str(tmp_path / "a.txt"), "--map", str(empty)]) == 1
