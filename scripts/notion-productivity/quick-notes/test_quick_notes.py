import pytest
import quick_notes as qn


def sample():
    data = {"next_id": 1, "notes": []}
    qn.add_note(data, "Buy oat milk #errands", "2026-01-05 09:10")
    qn.add_note(data, "Idea: rename receipts #ideas", "2026-01-05 14:22")
    qn.add_note(data, "Call the bank #errands #money", "2026-01-06 11:03")
    return data


def test_tags_of_ignores_urls_and_case():
    assert qn.tags_of("a #One and #two-x, #ONE") == ["one", "two-x"]
    assert qn.tags_of("issue#12 is not a tag") == []


def test_select_by_word_and_tag_newest_first():
    data = sample()
    assert [n["id"] for n in qn.select(data)] == [3, 2, 1]
    assert [n["id"] for n in qn.select(data, tag="#errands")] == [3, 1]
    assert [n["id"] for n in qn.select(data, word="BANK")] == [3]
    assert qn.select(data, word="zzz") == []


def test_tag_counts_sorted_by_frequency():
    assert qn.tag_counts(sample()) == {"errands": 2, "ideas": 1, "money": 1}


def test_cli_add_search_delete(tmp_path, capsys):
    f = str(tmp_path / "n.json")
    qn.main(["add", "Remember", "the", "milk", "#home", "--file", f, "--stamp", "2026-02-01 08:00"])
    capsys.readouterr()
    assert qn.main(["search", "milk", "--file", f]) == 0
    assert "2026-02-01 08:00  Remember the milk #home" in capsys.readouterr().out
    assert qn.main(["search", "nothing", "--file", f]) == 1
    assert qn.main(["delete", "1", "--file", f]) == 0
    assert qn.main(["delete", "1", "--file", f]) == 1


def test_argument_errors(tmp_path):
    f = str(tmp_path / "n.json")
    for bad in (["add"], ["delete", "abc"], ["search"]):
        with pytest.raises(SystemExit):
            qn.main([*bad, "--file", f])
