import pytest
import readability_scorer as rs

EASY = "The cat sat on the mat. It was a warm day. We went to the park to play."
HARD = ("Notwithstanding considerable organisational complexity, institutional stakeholders "
        "consistently demonstrated extraordinary administrative responsibilities throughout "
        "the implementation of comprehensive environmental regulations.")


@pytest.mark.parametrize("word,expected", [
    ("cat", 1), ("water", 2), ("beautiful", 3), ("the", 1), ("table", 2), ("jumped", 1),
    ("organisation", 5), ("rhythm", 1), ("", 0), ("123", 0)])
def test_syllables(word, expected):
    assert rs.count_syllables(word) == expected


def test_counts_and_flesch_formula():
    result = rs.analyse("One two three. Four five six.")
    assert result["words"] == 6 and result["sentences"] == 2
    expected = 206.835 - 1.015 * 3 - 84.6 * (1 + 1 + 1 + 1 + 1 + 1) / 6
    assert abs(result["ease"] - expected) < 1.5  # "three" and "five" are estimated


def test_easy_text_scores_easier_than_hard_text():
    easy, hard = rs.analyse(EASY), rs.analyse(HARD)
    assert easy["ease"] > 90 and hard["ease"] < 10
    assert easy["grade"] < 3 and hard["grade"] > 15
    assert rs.describe(easy["ease"]).startswith("very easy")
    assert rs.describe(hard["ease"]).startswith("very difficult")


def test_describe_boundaries():
    assert rs.describe(60).startswith("plain English")
    assert rs.describe(59.9).startswith("fairly diff")
    assert rs.describe(-20).startswith("very difficult")


def test_empty_text():
    assert rs.analyse("") is None and rs.analyse("123 ... !!!") is None


def test_cli_and_target_grade(tmp_path, capsys):
    easy, hard = tmp_path / "easy.txt", tmp_path / "hard.txt"
    easy.write_text(EASY)
    hard.write_text(HARD)
    assert rs.main([str(easy), "--target-grade", "8"]) == 0
    out = capsys.readouterr().out
    assert "easy.txt: 18 words, 3 sentences" in out and "Flesch-Kincaid" in out
    assert rs.main([str(hard), "--target-grade", "8"]) == 1
    assert "Too hard" in capsys.readouterr().out
    (tmp_path / "empty.txt").write_text("")
    assert rs.main([str(tmp_path / "empty.txt")]) == 1
    assert rs.main([str(tmp_path / "ghost.txt")]) == 1
