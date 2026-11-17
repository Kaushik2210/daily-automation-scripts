import pytest
import wordlist_spellcheck as wsc

KNOWN = {"the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog", "their", "friend"}


def test_finds_unknown_words_with_lines():
    found = wsc.find_unknown("The quick brwn fox\njumps over teh lazy brwn dog", KNOWN)
    assert dict(found) == {"brwn": [1, 2], "teh": [2]}


def test_ignores_urls_emails_code_short_and_shouting_words():
    text = "See https://zzz.example/x and bob@zzz.example or `codeword` and NASA and a b."
    assert dict(wsc.find_unknown(text, KNOWN | {"see", "and", "or"})) == {}


def test_possessives_and_capitalised_option():
    assert dict(wsc.find_unknown("The fox's Zorblax", KNOWN)) == {"zorblax": [1]}
    assert dict(wsc.find_unknown("The fox's Zorblax", KNOWN, ignore_capitalized=True)) == {}


def test_suggestions():
    assert wsc.suggest("thier", sorted(KNOWN))[:1] == ["their"]
    assert wsc.suggest("freind", sorted(KNOWN))[:1] == ["friend"]
    assert wsc.suggest("xqzvw", sorted(KNOWN)) == []


def test_cli_with_wordlist_and_allow_file(tmp_path, capsys):
    words = tmp_path / "words.txt"
    words.write_text("\n".join(sorted(KNOWN)) + "\n# comment\n")
    allow = tmp_path / "mine.txt"
    allow.write_text("Kaushik\n")
    doc = tmp_path / "doc.txt"
    doc.write_text("The quick brown fox jumpd over their lazy dog.\nKaushik and thier freind.\n")
    assert wsc.main([str(doc), "--wordlist", str(words), "--allow", str(allow)]) == 1
    out = capsys.readouterr().out
    assert "doc.txt: 4 unknown word(s)" in out and "jumpd" in out and "did you mean: jumps" in out
    assert "kaushik" not in out.lower().replace("kaushik and", "")
    doc.write_text("The quick brown fox.\n")
    assert wsc.main([str(doc), "--wordlist", str(words)]) == 0


def test_missing_inputs(tmp_path, capsys):
    words = tmp_path / "w.txt"
    words.write_text("fox\n")
    assert wsc.main([str(tmp_path / "gone.txt"), "--wordlist", str(words)]) == 1
    with pytest.raises(SystemExit):
        wsc.main([str(words), "--wordlist", str(tmp_path / "none.txt")])
