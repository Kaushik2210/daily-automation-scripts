import pytest
import text_summarizer as ts

ARTICLE = (
    "Solar power is growing quickly across the world. Solar panels are cheaper than ever before. "
    "My cat likes to sleep. Batteries let solar power work at night, so solar plants and batteries "
    "are built together. Dr. Smith visited the lake yesterday. Solar power could supply a quarter "
    "of electricity soon.")


def test_split_sentences_respects_abbreviations():
    parts = ts.split_sentences("Dr. Smith met Mr. Jones. They talked! Was it good? Yes it was.")
    assert parts == ["Dr. Smith met Mr. Jones.", "They talked!", "Was it good?", "Yes it was."]


def test_split_keeps_unterminated_tail():
    assert ts.split_sentences("One thing. and another") == ["One thing. and another"]
    assert ts.split_sentences("No end here") == ["No end here"]


def test_summary_prefers_sentences_about_the_main_topic_in_order():
    summary, total = ts.summarise(ARTICLE, 2)
    assert total == 6 and len(summary) == 2
    assert all("olar" in s for s in summary)
    assert "My cat likes to sleep." not in summary
    assert ARTICLE.index(summary[0]) < ARTICLE.index(summary[1])  # original order


def test_asking_for_more_than_exists_returns_all_long_enough():
    text = "Short one. This sentence contains several interesting content words."
    summary, _ = ts.summarise(text, 5)
    assert summary == ["This sentence contains several interesting content words."]


def test_cli(tmp_path, capsys):
    source = tmp_path / "a.txt"
    source.write_text(ARTICLE)
    assert ts.main([str(source), "-n", "2", "--bullets"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n- ") + out.startswith("- ") == 2 and "Kept 2 of 6 sentence(s)" in out
    tiny = tmp_path / "b.txt"
    tiny.write_text("Hi.")
    assert ts.main([str(tiny)]) == 1
    with pytest.raises(SystemExit):
        ts.main([str(tmp_path / "missing.txt")])
