import keyword_extractor as ke
import pytest


def test_tokens_drop_stopwords_and_short_words():
    text = "The cat and the DOG ran to a big park"
    assert ke.tokens(text) == ["cat", "dog", "ran", "big", "park"]


def test_single_document_ranks_by_frequency():
    ranked = ke.rank({"a": "solar solar solar panel panel wind"}, 2, False)
    assert [(k, c) for k, _, c in ranked["a"]] == [("solar", 3), ("panel", 2)]


def test_words_common_to_all_documents_rank_lower():
    docs = {"a": "energy solar solar energy", "b": "energy wind wind energy",
            "c": "energy battery battery energy"}
    top_a = ke.rank(docs, 3, False)["a"]
    assert top_a[0][0] == "solar"
    assert [k for k, _, _ in top_a].index("energy") > 0


def test_phrases_split_on_punctuation_and_stopwords():
    assert ke.phrases("wind turbines. offshore wind turbines, solar farms") == [
        "wind turbines", "offshore wind", "wind turbines", "solar farms"]
    assert "turbines offshore" not in ke.phrases("wind turbines. offshore wind")


def test_phrase_mode_prefers_repeated_phrases():
    ranked = ke.rank({"a": "wind turbines are big. wind turbines spin. solar farms"}, 2, True)
    assert ranked["a"][0][0] == "wind turbines" and ranked["a"][0][2] == 2


def test_cli_folder_and_missing(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("solar solar panel")
    (tmp_path / "b.md").write_text("wind wind turbine")
    (tmp_path / "skip.csv").write_text("ignored,me")
    assert ke.main([str(tmp_path), "--top", "1"]) == 0
    out = capsys.readouterr().out
    assert "a.txt  (3 words)" in out and "solar" in out and "b.md" in out and "skip.csv" not in out
    assert "weighted" in out
    assert ke.main([str(tmp_path / "nothing")]) == 1
    with pytest.raises(SystemExit):
        ke.main([str(tmp_path), "--top", "0"])
