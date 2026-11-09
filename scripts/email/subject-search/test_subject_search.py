import email
import email.policy

import pytest
import subject_search as ss

MBOX = (
    "From a@x.test Mon Sep 01 08:00:00 2026\nFrom: Ann <a@x.test>\nSubject: Invoice September\n"
    "Date: Tue, 01 Sep 2026 08:00:00 +0000\n\nbody\n\n"
    "From b@x.test Tue Sep 02 08:00:00 2026\nFrom: Bob <b@x.test>\n"
    "Subject: =?utf-8?q?Caf=C3=A9_invoice?=\nDate: Wed, 02 Sep 2026 08:00:00 +0000\n\nbody\n\n"
    "From c@x.test Wed Sep 03 08:00:00 2026\nFrom: Cy <c@x.test>\nSubject: Lunch\n\nbody\n")


def test_matches_needs_every_word_in_any_case():
    assert ss.matches("Invoice for September", ["invoice", "SEPT"])
    assert not ss.matches("Invoice for September", ["invoice", "october"])
    assert ss.matches("anything", []) and not ss.matches(None, ["x"])


def test_summary_decodes_headers():
    msg = email.message_from_string("From: A <a@x.test>\nSubject: =?utf-8?q?Caf=C3=A9?=\n\n",
                                    policy=email.policy.default)
    assert ss.summary(msg) == ("unknown date", "A <a@x.test>", "Café")


def test_mbox_search_matches_decoded_subjects(tmp_path, capsys):
    path = tmp_path / "mail.mbox"
    path.write_text(MBOX)
    assert ss.main(["invoice", "--mbox", str(path)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("2 match(es) for 'invoice' in 1 place(s):")
    assert out.index("Café invoice") < out.index("Invoice September")  # newest first
    assert "Lunch" not in out


def test_no_match_exits_1_and_limit_truncates(tmp_path, capsys):
    path = tmp_path / "mail.mbox"
    path.write_text(MBOX)
    assert ss.main(["nothing", "--mbox", str(path)]) == 1
    assert ss.main(["invoice", "--mbox", str(path), "--limit", "1"]) == 0
    assert "... 1 more not shown" in capsys.readouterr().out


def test_several_mbox_files_are_reported_separately(tmp_path, capsys):
    one, two = tmp_path / "one.mbox", tmp_path / "two.mbox"
    one.write_text(MBOX)
    two.write_text(MBOX.split("From c@x.test")[0])
    assert ss.main(["invoice", "--mbox", str(one), "--mbox", str(two)]) == 0
    out = capsys.readouterr().out
    assert "4 match(es)" in out and "one.mbox" in out and "two.mbox" in out


class FakeIMAP:
    def __init__(self):
        self.calls = []

    def list(self):
        return "OK", [b'(\\HasNoChildren) "/" "INBOX"', b'(\\Noselect \\HasChildren) "/" "[Gmail]"',
                      b'(\\HasNoChildren) "/" "Archive/2026"', b"(\\HasNoChildren) NIL Sent"]

    def select(self, folder, readonly=False):
        self.calls.append(("select", folder, readonly))
        return "OK", [b"1"]

    def search(self, charset, *criteria):
        self.calls.append(("search", charset, criteria))
        return "OK", [b"1"]

    def fetch(self, number, what):
        self.calls.append(("fetch", what))
        raw = b"From: Zed <z@x.test>\nSubject: Hit\nDate: Mon, 05 Oct 2026 09:00:00 +0000\n\n"
        return "OK", [(b"1 (BODY[HEADER.FIELDS] {5}", raw), b")"]

    def logout(self):
        pass


def test_list_folders_skips_noselect_and_reads_quoted_names():
    assert ss.list_folders(FakeIMAP()) == ["INBOX", "Archive/2026", "Sent"]


def test_imap_searches_every_folder_read_only(monkeypatch, capsys):
    fake = FakeIMAP()
    monkeypatch.setattr(ss, "connect", lambda: fake)
    assert ss.main(["Hit", "now"]) == 0
    selects = [c for c in fake.calls if c[0] == "select"]
    assert [c[1] for c in selects] == ['"INBOX"', '"Archive/2026"', '"Sent"']
    assert all(c[2] is True for c in selects)
    search = next(c for c in fake.calls if c[0] == "search")
    assert search[2] == ("SUBJECT", '"Hit"', "SUBJECT", '"now"')
    assert "3 match(es)" in capsys.readouterr().out


def test_non_ascii_terms_use_utf8_search(monkeypatch):
    fake = FakeIMAP()
    ss.search_folder(fake, "INBOX", ["café"])
    search = next(c for c in fake.calls if c[0] == "search")
    assert search[1] == "UTF-8" and search[2][1] == '"café"'.encode()


def test_errors(monkeypatch, capsys):
    monkeypatch.delenv("IMAP_HOST", raising=False)
    assert ss.main(["x"]) == 1
    with pytest.raises(SystemExit):
        ss.main(["x", "--mbox", "gone.mbox"])
