import email
import email.policy

import pytest
import unsubscribe_finder as uf


def msg(sender, subject, unsub=None, post=None):
    headers = f"From: {sender}\nSubject: {subject}\n"
    if unsub:
        headers += f"List-Unsubscribe: {unsub}\n"
    if post:
        headers += f"List-Unsubscribe-Post: {post}\n"
    return email.message_from_string(headers + "\nbody", policy=email.policy.default)


MBOX = (
    "From a@x.test Mon Sep 01 08:00:00 2026\nFrom: News <news@x.test>\nSubject: One\n"
    "List-Unsubscribe: <https://x.test/u?id=1>, <mailto:u@x.test>\n\nbody\n\n"
    "From a@x.test Tue Sep 02 08:00:00 2026\nFrom: News <news@x.test>\nSubject: Two\n"
    "List-Unsubscribe: <https://x.test/u?id=1>\n\nbody\n\n"
    "From f@x.test Wed Sep 03 08:00:00 2026\nFrom: Friend <friend@x.test>\nSubject: Hi\n\nhey\n")


def test_parse_links_splits_web_and_mail():
    web, mail = uf.parse_links("<https://a.test/u>, <mailto:stop@a.test?subject=x>, <ftp://no>")
    assert web == ["https://a.test/u"] and mail == ["stop@a.test?subject=x"]
    assert uf.parse_links(None) == ([], []) and uf.parse_links("junk") == ([], [])


def test_find_lists_groups_by_sender_and_ignores_normal_mail():
    found = uf.find_lists([
        msg("News <NEWS@x.test>", "A", "<https://x.test/u>", "List-Unsubscribe=One-Click"),
        msg("News <news@x.test>", "B", "<https://x.test/u>, <mailto:u@x.test>"),
        msg("Friend <f@x.test>", "No list here"),
        msg("Shop <shop@y.test>", "Sale", "<mailto:stop@y.test>")])
    assert sorted(found) == ["news@x.test", "shop@y.test"]
    news = found["news@x.test"]
    assert (news["count"], news["subject"], news["one_click"]) == (2, "B", True)
    assert news["web"] == ["https://x.test/u"] and news["mail"] == ["u@x.test"]
    assert found["shop@y.test"]["one_click"] is False


def test_cli_with_mbox(tmp_path, capsys):
    path = tmp_path / "m.mbox"
    path.write_text(MBOX)
    assert uf.main(["--mbox", str(path)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("1 sender(s) offer an unsubscribe link (3 message(s) checked).")
    assert "news@x.test (News) - 2 messages, latest: 'Two'" in out
    assert "web:  https://x.test/u?id=1" in out and "mail: u@x.test" in out
    assert "friend@x.test" not in out and "Nothing was changed" in out


def test_limit_only_checks_the_newest(tmp_path, capsys):
    path = tmp_path / "m.mbox"
    path.write_text(MBOX)
    assert uf.main(["--mbox", str(path), "--limit", "1"]) == 0
    assert "0 sender(s)" in capsys.readouterr().out


class FakeIMAP:
    def __init__(self):
        self.calls = []

    def select(self, folder, readonly=False):
        self.calls.append(("select", readonly))
        return "OK", [b"2"]

    def search(self, charset, criterion):
        return "OK", [b"1 2"]

    def fetch(self, number, what):
        self.calls.append(("fetch", what))
        n = int(number)
        header = f"From: S{n} <s{n}@x.test>\nList-Unsubscribe: <https://x.test/{n}>\n\n"
        return "OK", [(b"1 (BODY[HEADER.FIELDS] {10}", header.encode()), b")"]

    def logout(self):
        self.calls.append(("logout",))


def test_imap_mode_is_read_only_and_asks_for_headers_only(monkeypatch, capsys):
    fake = FakeIMAP()
    monkeypatch.setattr(uf, "connect", lambda: fake)
    assert uf.main([]) == 0
    assert ("select", True) in fake.calls and ("logout",) in fake.calls
    fetches = [c[1] for c in fake.calls if c[0] == "fetch"]
    assert fetches and all("PEEK[HEADER.FIELDS" in f for f in fetches)
    assert "2 sender(s)" in capsys.readouterr().out


def test_errors(monkeypatch, capsys):
    monkeypatch.delenv("IMAP_HOST", raising=False)
    assert uf.main([]) == 1
    assert "IMAP_HOST" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        uf.main(["--mbox", "nope.mbox"])
