import email
import email.policy

import email_digest as ed
import pytest

MBOX = """From a@x.test Mon Sep 01 08:00:00 2026
From: Ann <a@x.test>
Subject: Older unread
Date: Mon, 01 Sep 2026 08:00:00 +0000

First message body here.

From b@x.test Tue Sep 02 09:30:00 2026
From: Bob <b@x.test>
Subject: Already read
Date: Tue, 02 Sep 2026 09:30:00 +0000
Status: RO

You saw this one.

From c@x.test Wed Sep 03 10:00:00 2026
From: Cy <c@x.test>
Subject: =?utf-8?q?Caf=C3=A9_menu?=
Date: Wed, 03 Sep 2026 10:00:00 +0200
Content-Type: text/html

<p>Today: <b>soup</b></p>
"""


def raw(subject, body="Hello there"):
    return (f"From: Dee <d@x.test>\nSubject: {subject}\nDate: Thu, 04 Sep 2026 11:00:00 +0000\n"
            f"\n{body}\n").encode()


class FakeIMAP:
    """Just enough of imaplib for the digest; records what was asked."""

    def __init__(self, messages):
        self.messages, self.calls, self.logged_out = messages, [], False

    def select(self, folder, readonly=False):
        self.calls.append(("select", folder, readonly))
        return "OK", [b"1"]

    def search(self, charset, criterion):
        self.calls.append(("search", criterion))
        return "OK", [b" ".join(str(i + 1).encode() for i in range(len(self.messages)))]

    def fetch(self, number, what):
        self.calls.append(("fetch", number, what))
        body = self.messages[int(number) - 1]
        return "OK", [(b"%s (RFC822.SIZE 4321 BODY[]<0> {%d}" % (number, len(body)), body), b")"]

    def logout(self):
        self.logged_out = True


@pytest.fixture
def mbox(tmp_path):
    path = tmp_path / "in.mbox"
    path.write_text(MBOX)
    return path


def test_human_size():
    assert [ed.human_size(n) for n in (5, 2048, 3 * 1024 * 1024)] == ["5 B", "2.0 KB", "3.0 MB"]


def test_mbox_skips_read_mail_unless_asked(mbox):
    unread = ed.from_mbox(mbox, False, 50)
    assert [m["subject"] for m in unread] == ["Older unread", "Café menu"]
    assert len(ed.from_mbox(mbox, True, 50)) == 3


def test_snippets_handle_plain_html_and_truncation(mbox):
    first, html = ed.from_mbox(mbox, False, 12)
    assert first["snippet"] == "First mes..."
    assert ed.from_mbox(mbox, False, 200)[1]["snippet"] == "Today: soup"
    assert ed.from_mbox(mbox, False, 0)[0]["snippet"] == ""


def test_dates_are_normalised_to_utc():
    msg = email.message_from_string("Date: Wed, 03 Sep 2026 10:00:00 +0200\n\nx",
                                    policy=email.policy.default)
    assert ed.message_date(msg).strftime("%H:%M") == "08:00"
    assert ed.message_date(email.message_from_string("Subject: x\n\ny")) is None


def test_cli_lists_newest_first(mbox, capsys):
    assert ed.main(["--mbox", str(mbox)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("2 unread message(s) in")
    assert out.index("Café menu") < out.index("Older unread")
    assert "(" in out and "Today: soup" in out
    assert ed.main(["--mbox", str(mbox), "--all", "--limit", "1"]) == 0
    assert "showing the newest 1" in capsys.readouterr().out


def test_imap_is_opened_read_only_and_uses_peek(monkeypatch, capsys):
    fake = FakeIMAP([raw("One"), raw("Two", "<p>Hi</p>")])
    monkeypatch.setattr(ed, "connect", lambda: fake)
    assert ed.main(["--limit", "5"]) == 0
    assert ("select", '"INBOX"', True) in fake.calls
    assert ("search", "UNSEEN") in fake.calls
    assert all("PEEK" in call[2] for call in fake.calls if call[0] == "fetch")
    assert fake.logged_out and "One" in capsys.readouterr().out


def test_imap_limit_and_failures(monkeypatch, capsys):
    fake = FakeIMAP([raw(str(n)) for n in range(5)])
    messages = ed.from_imap(fake, "INBOX", False, 2, 20)
    assert [m["subject"] for m in messages] == ["3", "4"] and messages[0]["size"] == 4321
    monkeypatch.delenv("IMAP_HOST", raising=False)
    assert ed.main([]) == 1
    assert "IMAP_HOST" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        ed.main(["--mbox", "missing.mbox"])
