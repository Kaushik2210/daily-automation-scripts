import csv

import data_anonymizer as da
import pytest

HEADER = ["id", "Full Name", "e-mail", "Mobile", "notes", "ip_address", "ssn", "joined"]
ROWS = [["1", "Ada Lovelace", "ada@example.com", "+91 98765 43210", "call ada@example.com",
         "8.8.8.8", "123-45-6789", "2024-03-12"],
        ["2", "Bob Smith", "bob@example.org", "(555) 201-3344", "", "1.1.1.1", "", "2023-01-02"],
        ["3", "Ada Lovelace", "ada@example.com", "", "n/a", "8.8.8.8", "987", "2024-03-12"]]


def test_detect_by_header_and_content():
    found = da.detect(HEADER, ROWS)
    assert found == {"Full Name": "name", "e-mail": "email", "Mobile": "phone",
                     "ip_address": "ip", "ssn": "redact"}
    unnamed = da.detect(["id", "contact"], [["1", "a@b.co"], ["2", "c@d.org"], ["3", "e@f.net"]])
    assert unnamed == {"contact": "email"}
    assert da.detect(["id", "x"], [["1", "a@b.co"], ["2", "plain"], ["3", "text"]]) == {}


def test_masks_are_consistent_and_salted():
    first = da.mask("ada@example.com", "email", "s1")
    assert first == da.mask("ADA@example.com ", "email", "s1")
    assert first != da.mask("ada@example.com", "email", "s2")
    assert first.startswith("user_") and first.endswith("@example.com")
    name = da.mask("Ada", "name", "s1")
    assert len(name.split()) == 2 and name == da.mask("ada", "name", "s1")


def test_phone_card_ip_and_other_kinds():
    assert da.mask("+91 98765 43210", "phone", "s") == "+XX XXXXX XXX10"
    assert da.mask("(555) 201-3344", "phone", "s") == "(XXX) XXX-XX44"
    assert da.mask("4111 1111 1111 1111", "card", "s") == "**** **** **** 1111"
    ip = da.mask("8.8.8.8", "ip", "s")
    assert ip.startswith("10.") and ip == da.mask("8.8.8.8", "ip", "s")
    assert da.mask("x", "redact", "s") == "[REDACTED]"
    assert da.mask("2024-03-12", "year", "s") == "2024" and da.mask("soon", "year", "s") == "[date]"
    assert len(da.mask("anything", "hash", "s")) == 10
    assert da.mask("mail ada@example.com or call +91 98765 43210", "scrub", "s") == (
        "mail [email] or call [phone]")


def test_anonymise_keeps_empty_values_and_counts_changes():
    plan = {"e-mail": "email", "Mobile": "phone"}
    result, changed = da.anonymise(HEADER, ROWS, plan, "s")
    assert result[2][3] == "" and result[0][2] == result[2][2]  # same person, same pseudonym
    assert changed == {"e-mail": 3, "Mobile": 2}
    assert result[0][0] == "1" and ROWS[0][2] == "ada@example.com"  # input untouched


def write(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    return path


def test_cli_dry_run_apply_and_no_overwrite(tmp_path, capsys):
    source = write(tmp_path / "people.csv", HEADER, ROWS)
    assert da.main([str(source)]) == 0
    out = capsys.readouterr().out
    assert "5 column(s) to mask" in out and "Full Name" in out and "(detected)" in out
    assert "Dry run" in out and not (tmp_path / "people.anonymized.csv").exists()
    assert da.main([str(source), "--apply", "--keep", "ip_address", "--salt", "k"]) == 0
    with (tmp_path / "people.anonymized.csv").open(encoding="utf-8") as handle:
        result = list(csv.reader(handle))
    assert result[0] == HEADER and result[1][5] == "8.8.8.8"
    assert "ada@example.com" not in "".join(map(str, result)).replace("call ada@example.com", "")
    assert da.main([str(source), "--apply"]) == 1
    assert "already exists" in capsys.readouterr().err


def test_explicit_masks_and_errors(tmp_path, capsys):
    source = write(tmp_path / "p.csv", HEADER, ROWS)
    assert da.main([str(source), "--no-auto", "--mask", "notes:scrub"]) == 0
    out = capsys.readouterr().out
    assert "1 column(s) to mask" in out and "(chosen)" in out and "[email]" in out
    assert da.main([str(source), "--no-auto"]) == 1
    assert "No personal-data columns" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        da.main([str(source), "--mask", "ghost:email"])
    with pytest.raises(SystemExit):
        da.main([str(source), "--mask", "notes:magic"])
    empty = tmp_path / "e.csv"
    empty.write_text("")
    assert da.main([str(empty)]) == 1
