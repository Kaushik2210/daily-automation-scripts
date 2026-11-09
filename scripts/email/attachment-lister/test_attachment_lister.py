import email
import email.policy
from email.message import EmailMessage

import attachment_lister as al
import pytest


def build(subject, files=(), inline=False):
    msg = EmailMessage()
    msg["From"], msg["Subject"] = "Ann <ann@x.test>", subject
    msg["Date"] = "Mon, 05 Oct 2026 09:00:00 +0000"
    msg.set_content("Hello")
    for name, size in files:
        msg.add_attachment(b"x" * size, maintype="application", subtype="pdf", filename=name)
    if inline:
        msg.add_attachment(b"y" * 10, maintype="text", subtype="plain",
                           disposition="attachment")
    return msg


def to_mbox(messages):
    return "".join(f"From ann@x.test Mon Oct 05 09:00:00 2026\n{m.as_string()}\n"
                   for m in messages)


def test_human_size():
    assert [al.human_size(n) for n in (10, 1536, 5 * 1024 ** 2, 3 * 1024 ** 3)] == [
        "10 B", "1.5 KB", "5.0 MB", "3.0 GB"]


def test_attachments_of_reads_names_types_and_decoded_sizes():
    msg = build("Files", [("a.pdf", 2000), ("b.pdf", 30)], inline=True)
    parsed = email.message_from_bytes(msg.as_bytes(), policy=email.policy.default)
    assert al.attachments_of(parsed) == [
        ("a.pdf", "application/pdf", 2000), ("b.pdf", "application/pdf", 30),
        ("(unnamed)", "text/plain", 10)]
    plain = email.message_from_bytes(build("None").as_bytes(), policy=email.policy.default)
    assert al.attachments_of(plain) == []


def test_describe_handles_missing_headers():
    assert al.describe(email.message_from_string("\nbody")) == (
        "unknown date", "(unknown sender)", "(no subject)")


def test_cli_lists_only_messages_with_files(tmp_path, capsys):
    path = tmp_path / "m.mbox"
    path.write_text(to_mbox([build("Plain note"), build("Big one", [("deck.pdf", 4096)]),
                             build("Two", [("a.pdf", 100), ("b.pdf", 200)])]))
    assert al.main(["--mbox", str(path)]) == 0
    out = capsys.readouterr().out
    assert "Plain note" not in out and "Big one" in out
    assert "- deck.pdf  (4.0 KB, application/pdf)" in out
    assert "2 of 3 message(s) have attachments: 3 file(s), 4.3 KB in total." in out


def test_min_kb_filters_small_files(tmp_path, capsys):
    path = tmp_path / "m.mbox"
    path.write_text(to_mbox([build("Two", [("small.pdf", 100), ("large.pdf", 5000)])]))
    assert al.main(["--mbox", str(path), "--min-kb", "1"]) == 0
    out = capsys.readouterr().out
    assert "large.pdf" in out and "small.pdf" not in out and "1 file(s)" in out


class FakeIMAP:
    def __init__(self, raws):
        self.raws, self.calls = raws, []

    def select(self, folder, readonly=False):
        self.calls.append(("select", readonly))
        return "OK", [b"1"]

    def search(self, charset, criterion):
        return "OK", [b" ".join(str(i + 1).encode() for i in range(len(self.raws)))]

    def fetch(self, number, what):
        self.calls.append(("fetch", what))
        return "OK", [(b"1 (BODY[] {5}", self.raws[int(number) - 1]), b")"]

    def logout(self):
        pass


def test_imap_is_read_only(monkeypatch, capsys):
    fake = FakeIMAP([build("Remote", [("r.pdf", 700)]).as_bytes()])
    monkeypatch.setattr(al, "connect", lambda: fake)
    assert al.main([]) == 0
    assert ("select", True) in fake.calls and ("fetch", "(BODY.PEEK[])") in fake.calls
    assert "r.pdf" in capsys.readouterr().out


def test_errors(monkeypatch, capsys):
    monkeypatch.delenv("IMAP_HOST", raising=False)
    assert al.main([]) == 1
    with pytest.raises(SystemExit):
        al.main(["--mbox", "gone.mbox"])
