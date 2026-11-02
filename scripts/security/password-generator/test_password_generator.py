import string

import password_generator as pg
import pytest


def test_password_has_every_kind_and_right_length():
    for _ in range(50):
        pw = pg.make_password(12)
        assert len(pw) == 12
        assert any(c in string.ascii_lowercase for c in pw)
        assert any(c in string.ascii_uppercase for c in pw)
        assert any(c in string.digits for c in pw)
        assert any(c in pg.SYMBOLS for c in pw)


def test_no_symbols_and_no_ambiguous():
    for _ in range(50):
        pw = pg.make_password(20, symbols=False, avoid_ambiguous=True)
        assert all(c in string.ascii_letters + string.digits for c in pw)
        assert not set(pw) & set(pg.AMBIGUOUS)


def test_too_short_rejected():
    with pytest.raises(ValueError):
        pg.make_password(3)


def test_passphrase_shape_and_wordlist():
    assert len(pg.WORDS) == len(set(pg.WORDS)) >= 128
    phrase = pg.make_passphrase(4, separator=".", capitalize=True)
    parts = phrase.split(".")
    assert len(parts) == 4 and all(p.lower() in pg.WORDS for p in parts)


def test_cli_count_and_entropy_note(capsys):
    pg.main(["-n", "3", "-l", "10"])
    assert len(capsys.readouterr().out.split()) == 3
    pg.main(["--passphrase", "5"])
    assert "bits" in capsys.readouterr().err
