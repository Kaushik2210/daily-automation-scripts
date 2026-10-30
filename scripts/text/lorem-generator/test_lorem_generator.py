import pytest
from lorem_generator import OPENING, generate, main, words


def test_paragraph_and_sentence_counts():
    paragraphs = generate(paragraphs=4, sentences=3, seed=1)
    assert len(paragraphs) == 4
    assert all(p.count(". ") + 1 == 3 or p.endswith(".") for p in paragraphs)


def test_classic_start_and_seed_repeatable():
    assert generate(seed=7)[0].startswith(OPENING)
    assert generate(seed=7) == generate(seed=7)
    assert not generate(seed=7, classic_start=False)[0].startswith(OPENING)


def test_word_count_is_exact():
    assert len(words(25, seed=3).split()) == 25


def test_cli_rejects_zero(capsys):
    with pytest.raises(SystemExit):
        main(["-p", "0"])
    main(["-w", "5", "--seed", "2"])
    assert len(capsys.readouterr().out.split()) == 5
