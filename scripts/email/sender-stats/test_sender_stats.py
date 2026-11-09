import pytest
import sender_stats as ss

ITEMS = [("Ann <ann@acme.test>", 1000), ("ANN <Ann@Acme.test>", 2000), ("Bob <bob@acme.test>", 500),
         ("news@brief.example", 300), (None, 10)]


def test_sender_key():
    assert ss.sender_key("Ann <Ann@Acme.TEST>", "address") == "ann@acme.test"
    assert ss.sender_key("Ann <Ann@Acme.TEST>", "domain") == "acme.test"
    assert ss.sender_key(None, "address") == "(unknown)"
    assert ss.sender_key("garbage", "domain") == "garbage"  # no @, so the whole text is kept


def test_rank_counts_sizes_and_orders_ties():
    ranking = ss.rank(ITEMS)
    assert ranking[0] == ("ann@acme.test", 2, 3000)
    assert ranking[1:] == [("bob@acme.test", 1, 500), ("news@brief.example", 1, 300),
                           ("(unknown)", 1, 10)]  # ties are broken by total size
    by_domain = ss.rank(ITEMS, "domain")
    assert by_domain[0] == ("acme.test", 3, 3500)


def test_human_size():
    assert [ss.human_size(n) for n in (1, 1024, 1048576)] == ["1 B", "1.0 KB", "1.0 MB"]


MBOX = ("From a@x.test Mon Sep 01 08:00:00 2026\nFrom: A <a@x.test>\nSubject: 1\n\nhello\n\n"
        "From a@x.test Tue Sep 02 08:00:00 2026\nFrom: A <a@x.test>\nSubject: 2\n\nagain\n\n"
        "From b@y.test Wed Sep 03 08:00:00 2026\nFrom: B <b@y.test>\nSubject: 3\n\nhi\n")


def test_cli_ranks_an_mbox(tmp_path, capsys):
    path = tmp_path / "m.mbox"
    path.write_text(MBOX)
    assert ss.main(["--mbox", str(path)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "3 message(s) from 2 address(es):"
    assert lines[2].startswith("a@x.test") and "66.7%" in lines[2]
    assert lines[3].startswith("b@y.test") and "33.3%" in lines[3]


def test_top_limit_and_limit_newest(tmp_path, capsys):
    path = tmp_path / "m.mbox"
    path.write_text(MBOX)
    assert ss.main(["--mbox", str(path), "--top", "1"]) == 0
    assert "... and 1 more." in capsys.readouterr().out
    assert ss.main(["--mbox", str(path), "--limit", "1", "--by", "domain"]) == 0
    assert "1 message(s) from 1 domain(es)" in capsys.readouterr().out


class FakeIMAP:
    def __init__(self):
        self.calls = []

    def select(self, folder, readonly=False):
        self.calls.append(("select", readonly))
        return "OK", [b"3"]

    def search(self, charset, criterion):
        return "OK", [b"1 2 3"]

    def fetch(self, numbers, what):
        self.calls.append(("fetch", numbers, what))
        rows = [(b"1 (RFC822.SIZE 100 BODY[HEADER.FIELDS (FROM)] {20}", b"From: A <a@x.test>\n\n"),
                b")",
                (b"2 (RFC822.SIZE 300 BODY[HEADER.FIELDS (FROM)] {20}", b"From: A <a@x.test>\n\n"),
                b")"]
        return "OK", rows

    def logout(self):
        pass


def test_imap_makes_one_read_only_request(monkeypatch, capsys):
    fake = FakeIMAP()
    monkeypatch.setattr(ss, "connect", lambda: fake)
    assert ss.main(["--limit", "3"]) == 0
    assert ("select", True) in fake.calls
    fetches = [c for c in fake.calls if c[0] == "fetch"]
    assert len(fetches) == 1 and fetches[0][1] == "1,2,3" and "PEEK" in fetches[0][2]
    assert "a@x.test" in capsys.readouterr().out


def test_errors(monkeypatch, capsys):
    monkeypatch.delenv("IMAP_HOST", raising=False)
    assert ss.main([]) == 1
    with pytest.raises(SystemExit):
        ss.main(["--mbox", "gone.mbox"])
    with pytest.raises(SystemExit):
        ss.main(["--mbox", "gone.mbox", "--top", "0"])
