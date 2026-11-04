import journal_cli as jc

BASE = "# Journal\n\n## 2026-01-05\n\n- 09:10 walk\n- 18:45 draft\n"


def test_add_to_existing_day_keeps_order():
    out = jc.add_entry(BASE, "email", "2026-01-05", "20:00")
    assert out.splitlines()[-1] == "- 20:00 email"
    assert out.count("## 2026-01-05") == 1


def test_add_new_day_sorted_and_from_empty():
    out = jc.add_entry(BASE, "plan", "2026-01-03", "08:00")
    assert out.index("## 2026-01-03") < out.index("## 2026-01-05")
    fresh = jc.add_entry("", "first", "2026-02-01", "07:30")
    assert fresh == "# Journal\n\n## 2026-02-01\n\n- 07:30 first\n"


def test_recent_and_search():
    text = jc.add_entry(BASE, "read a book", "2026-01-06", "21:00")
    assert [d for d, _ in jc.recent(text, 1)] == ["2026-01-06"]
    assert jc.search(text, "DRAFT") == [("2026-01-05", "- 18:45 draft")]
    assert jc.search(text, "zzz") == []


def test_cli_add_show_search(tmp_path, capsys):
    f = str(tmp_path / "j.md")
    jc.main(["Went", "for", "a", "run", "--date", "2026-03-01", "--time", "07:15", "--file", f])
    jc.main(["Lunch with Sam", "--date", "2026-03-02", "--time", "12:30", "--file", f])
    capsys.readouterr()
    jc.main(["--show", "1", "--file", f])
    assert "2026-03-02" in capsys.readouterr().out
    assert jc.main(["--search", "run", "--file", f]) == 0
    assert jc.main(["--search", "nothing", "--file", f]) == 1


def test_bad_date_rejected(tmp_path):
    import pytest
    with pytest.raises(SystemExit):
        jc.main(["x", "--date", "01/02/2026", "--file", str(tmp_path / "j.md")])
