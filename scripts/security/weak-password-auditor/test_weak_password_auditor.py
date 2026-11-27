import json
import math

import pytest
import weak_password_auditor as wpa

CSV = """site,username,password
mail.example.com,ada,Summer2024!
shop.example.com,ada,Summer2024!
forum.example.com,ada,password123
bank.example.com,ada,Tr0ub4dor&3xK9v
social.example.com,ada,Summer2025!
work-vpn,ada,qwertyuiop
blog.example.com,ada,ada1990
notes.example.com,ada,k7#Vq2$mP9!zLw4x
game.example.com,ada,letmein
cloud.example.com,ada,k7#Vq2$mP9!zLw4x
"""


def messages(password, label=""):
    return " | ".join(m for _, m in wpa.problems(password, label))


def test_entropy_and_pool():
    assert wpa.pool_size("abc") == 26 and wpa.pool_size("aB3") == 62
    assert wpa.pool_size("aB3!") == 95 and wpa.pool_size("") == 1
    assert wpa.entropy_bits("abcd") == pytest.approx(4 * math.log2(26))


def test_base_of_strips_the_tail():
    assert wpa.base_of("Summer2025!") == "summer" and wpa.base_of("pass_word") == "pass_word"
    assert wpa.base_of("hello!!12") == "hello"


@pytest.mark.parametrize("password,expected", [
    ("password123", "very common"), ("letmein", "very common"), ("Passw0rd!", "very common"),
    ("abc", "only 3 characters"), ("Zq9!mK2x", "short (8 characters"),
    ("qwertyZ9!xyzAB", "keyboard or number sequence"), ("aaaaB7!xQ9mZpL", "repeats"),
    ("abcabcabcabc", "repeats"), ("Dolphin2019!", "word followed by a year"),
    ("Winter42!!xyz", "season or month")])
def test_individual_checks(password, expected):
    assert expected in messages(password)


def test_account_name_inside_the_password():
    assert "site or account name" in messages("Github-9XqL2mZv!", "github.com")
    assert "site or account name" not in messages("Github-9XqL2mZv!", "bank")
    assert "site or account name" not in messages("Gx9!", "git")  # labels shorter than 4 ignored


def test_a_long_random_password_has_no_problems():
    assert wpa.problems("k7#Vq2$mP9!zLw4x") == []
    assert wpa.rating([], False) == "strong"


def test_letters_only_is_only_fair():
    assert wpa.problems("kqzvbxmwyplhgtnr")[0][0] == "fair"


def test_rating_and_score():
    assert wpa.rating([("weak", "x"), ("fair", "y")], False) == "weak"
    assert wpa.rating([], True) == "critical"  # even a strong password is critical when reused
    strong = wpa.score("k7#Vq2$mP9!zLw4x", [], False)
    assert strong > 90 and wpa.score("k7#Vq2$mP9!zLw4x", [], True) == strong - 40
    assert wpa.score("abc", [("critical", "x")], False) == 0


def test_mask_never_reveals_the_password():
    masked = wpa.mask("Summer2024!")
    assert masked == "S********** (11 chars)" and "ummer" not in masked
    assert wpa.mask("") == " (0 chars)"
    assert len(wpa.mask("x" * 50)) < 30


def test_read_entries_csv_and_plain_lines():
    entries = wpa.read_entries(CSV, "password", None)
    assert entries[0] == ("mail.example.com", "Summer2024!") and len(entries) == 10
    assert wpa.read_entries("a,b\n1,2\n", "password", None)[0] == ("line 1", "a,b")  # not csv
    assert wpa.read_entries("one\n\ntwo\r\n", "password", None) == [("line 1", "one"),
                                                                       ("line 3", "two")]
    custom = wpa.read_entries("Name,Pass,Note\nbank,s3cret!,x\n", "Pass", "Name")
    assert custom == [("bank", "s3cret!")]
    assert wpa.read_entries("", "password", None) == []


def test_audit_finds_reuse_variations_and_ratings():
    results, groups = wpa.audit(wpa.read_entries(CSV, "password", None))
    by_label = {r["label"]: r for r in results}
    assert sorted(groups, key=len) == [["mail.example.com", "shop.example.com"],
                                       ["cloud.example.com", "notes.example.com"]]
    mail = by_label["mail.example.com"]
    assert mail["reused"] and mail["rating"] == "critical"
    assert any("variations" in m for _, m in by_label["social.example.com"]["issues"])
    assert by_label["forum.example.com"]["rating"] == "critical"
    assert by_label["bank.example.com"]["rating"] == "strong"
    assert by_label["notes.example.com"]["reused"]  # strong, but shared
    assert by_label["notes.example.com"]["rating"] == "critical"


def test_cli_text_never_prints_a_password(tmp_path, capsys):
    path = tmp_path / "p.csv"
    path.write_text(CSV, encoding="utf-8")
    assert wpa.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert "Audited 10 password(s)" in out and "Reused passwords:" in out
    assert "2 accounts share one password: mail.example.com, shop.example.com" in out
    for password in ("Summer2024!", "password123", "Tr0ub4dor&3xK9v", "qwertyuiop",
                     "k7#Vq2$mP9!zLw4x", "letmein"):
        assert password not in out
    assert "[CRITICAL] forum.example.com" in out and "bank.example.com" not in out.split(
        "Reused passwords:")[0]


def test_cli_json_and_fail_on(tmp_path, capsys):
    path = tmp_path / "p.csv"
    path.write_text(CSV, encoding="utf-8")
    assert wpa.main([str(path), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["counts"]["critical"] >= 5 and len(data["entries"]) == 10
    assert all(e["password"] != "Summer2024!" for e in data["entries"])
    assert wpa.main([str(path), "--fail-on", "critical"]) == 1
    capsys.readouterr()
    good = tmp_path / "g.txt"
    good.write_text("k7#Vq2$mP9!zLw4x\nvB4$nR8!tY2@qWz7\n")
    assert wpa.main([str(good), "--fail-on", "fair"]) == 0
    assert "0 critical, 0 weak, 0 fair, 2 strong" in capsys.readouterr().out


def test_cli_errors(tmp_path, capsys):
    assert wpa.main([str(tmp_path / "none.csv")]) == 1
    empty = tmp_path / "e.txt"
    empty.write_text("\n\n")
    assert wpa.main([str(empty)]) == 1
    assert "No passwords found" in capsys.readouterr().err
