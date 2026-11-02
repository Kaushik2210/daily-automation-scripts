from password_strength_checker import analyze, entropy_bits, has_sequence, main, pool_size


def test_pool_and_entropy():
    assert pool_size("abc") == 26
    assert pool_size("aB3!") == 26 + 26 + 10 + 33
    assert entropy_bits("") == 0
    assert entropy_bits("abcdefgh") < entropy_bits("aB3!aB3!")


def test_sequences_and_repeats():
    assert has_sequence("xx1234yy") and has_sequence("QWERty") and has_sequence("dcba9")
    assert not has_sequence("x7Qm#2")
    _, problems = analyze("aaabbb999")
    assert any("repeats" in p for p in problems)


def test_common_password_scores_zero():
    score, problems = analyze("Password1!")
    assert score == 0 and "is a very common password" in problems


def test_strong_passphrase():
    score, problems = analyze("correct-Horse-battery-7-staple!")
    assert score == 4 and problems == []


def test_cli_never_echoes_password(capsys):
    code = main(["hunter2hunter2"])
    out = capsys.readouterr().out
    assert "hunter2hunter2" not in out
    assert "Strength:" in out and code in (0, 1)
