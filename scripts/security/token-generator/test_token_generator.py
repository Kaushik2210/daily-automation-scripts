import re
import uuid

import pytest
import token_generator as tg


def test_hex_length_and_charset():
    token = tg.make_token("hex", 16)
    assert len(token) == 32 and re.fullmatch(r"[0-9a-f]+", token)


def test_urlsafe_and_base32_charsets():
    assert re.fullmatch(r"[A-Za-z0-9_-]+", tg.make_token("urlsafe", 24))
    assert re.fullmatch(r"[A-Z2-7]+", tg.make_token("base32", 10))


def test_numeric_and_uuid_and_prefix():
    assert re.fullmatch(r"\d{6}", tg.make_token("numeric", 6))
    assert uuid.UUID(tg.make_token("uuid")).version == 4
    assert tg.make_token("hex", 4, prefix="sk_").startswith("sk_")


def test_tokens_are_unique():
    assert len({tg.make_token("hex", 16) for _ in range(100)}) == 100


def test_unknown_kind_and_bad_cli_args(capsys):
    with pytest.raises(ValueError):
        tg.make_token("nope")
    with pytest.raises(SystemExit):
        tg.main(["--kind", "numeric", "-b", "2"])
    tg.main(["-n", "3", "--kind", "hex", "-b", "8"])
    assert len(capsys.readouterr().out.split()) == 3
