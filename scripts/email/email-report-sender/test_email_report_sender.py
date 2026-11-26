import socketserver
import threading

import email_report_sender as ers
import pytest


class FakeSMTP(socketserver.StreamRequestHandler):
    """A tiny SMTP server: records messages, refuses recipients containing 'refused'."""

    def reply(self, text):
        self.wfile.write((text + "\r\n").encode())

    def handle(self):
        self.reply("220 fake ready")
        recipients, data = [], None
        while True:
            line = self.rfile.readline().decode(errors="replace").rstrip("\r\n")
            command = line.upper()
            if command.startswith("EHLO") or command.startswith("HELO"):
                self.reply("250 fake")
            elif command.startswith("MAIL FROM"):
                self.reply("250 ok")
            elif command.startswith("RCPT TO"):
                if "refused" in line:
                    self.reply("550 no such user")
                else:
                    recipients.append(line.split(":", 1)[1].strip("<> "))
                    self.reply("250 ok")
            elif command == "DATA":
                self.reply("354 go")
                chunks = []
                while (row := self.rfile.readline().decode(errors="replace")) not in (".\r\n", ""):
                    chunks.append(row)
                data = "".join(chunks)
                self.server.inbox.append((recipients, data))
                self.reply("250 queued")
            elif command == "QUIT":
                self.reply("221 bye")
                return
            elif not line:
                return
            else:
                self.reply("250 ok")


@pytest.fixture
def smtp_server():
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), FakeSMTP)
    server.inbox = []
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


@pytest.fixture
def files(tmp_path):
    body = tmp_path / "body.txt"
    body.write_text("Hello team\n" + "\n".join(f"line {i}" for i in range(20)), encoding="utf-8")
    report = tmp_path / "report.csv"
    report.write_bytes(b"a,b\n1,2\n")  # exact bytes: write_text would add \r on Windows
    return body, report


def test_build_message_with_html_and_attachment(files):
    body, report = files
    message = ers.build_message("me@example.com", ["a@example.com", "b@example.com"],
                                ["c@example.com"], "Weekly", body.read_text(), "<p>Hi</p>",
                                [report])
    assert message["To"] == "a@example.com, b@example.com" and message["Cc"] == "c@example.com"
    kinds = [part.get_content_type() for part in message.walk()]
    assert kinds[:1] == ["multipart/mixed"] and "multipart/alternative" in kinds
    assert "text/plain" in kinds and "text/html" in kinds and "text/csv" in kinds
    attachment = next(message.iter_attachments())
    assert attachment.get_filename() == "report.csv" and attachment.get_content() == "a,b\n1,2\n"


@pytest.mark.parametrize("bad", ["nobody", "a@b", "two words@x.com", "a@x.com,b@x.com",
                                 "<a@x.com>"])
def test_addresses_are_checked(bad):
    with pytest.raises(ValueError):
        ers.check_address(bad)
    assert ers.check_address("ok.name+tag@sub.example.com")


def test_header_injection_is_refused(files):
    body, _ = files
    with pytest.raises(ValueError, match="line breaks"):
        ers.build_message("me@example.com", ["a@example.com"], [], "Hi\nBcc: evil@x.com",
                          "x", None, [])


def test_attachment_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(ers, "MAX_ATTACHMENT_BYTES", 10)
    big = tmp_path / "big.bin"
    big.write_bytes(b"x" * 11)
    with pytest.raises(ValueError, match="over"):
        ers.build_message("me@example.com", ["a@example.com"], [], "s", "b", None, [big])


def test_preview_is_the_default_and_never_connects(files, monkeypatch, capsys):
    body, report = files

    def boom(*args, **kwargs):
        raise AssertionError("must not connect during a preview")

    monkeypatch.setattr(ers.smtplib, "SMTP", boom)
    monkeypatch.setattr(ers.smtplib, "SMTP_SSL", boom)
    assert ers.main(["--to", "a@example.com", "--bcc", "hidden@example.com", "--from",
                     "me@example.com", "--subject", "Weekly", "--body-file", str(body),
                     "--attach", str(report)]) == 0
    out = capsys.readouterr().out
    assert "Preview (nothing sent)" in out and "Subject: Weekly" in out
    assert "report.csv  (8 bytes)" in out and "2 recipient(s)" in out
    assert "hidden@example.com" not in out and "1 hidden recipient(s)" in out
    assert "6 more line(s)" in out and "Add --send" in out


def test_send_through_a_fake_server(files, smtp_server, monkeypatch, capsys):
    body, report = files
    port = smtp_server.server_address[1]
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.delenv("SMTP_USER", raising=False)
    assert ers.main(["--to", "a@example.com", "--cc", "c@example.com", "--bcc", "b@example.com",
                     "--from", "me@example.com", "--subject", "Weekly", "--body-file", str(body),
                     "--attach", str(report), "--security", "none", "--smtp-port", str(port),
                     "--send"]) == 0
    assert "Sent to 3 recipient(s)" in capsys.readouterr().out
    recipients, data = smtp_server.inbox[0]
    assert recipients == ["a@example.com", "c@example.com", "b@example.com"]
    assert "Subject: Weekly" in data and "Bcc" not in data and "filename=\"report.csv\"" in data


def test_refused_recipient_is_reported(files, smtp_server, monkeypatch, capsys):
    body, _ = files
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    code = ers.main(["--to", "refused@example.com", "--from", "me@example.com", "--subject", "s",
                     "--body-file", str(body), "--security", "none", "--smtp-port",
                     str(smtp_server.server_address[1]), "--send"])
    assert code == 1 and "Couldn't send the email" in capsys.readouterr().err
    assert smtp_server.inbox == []


def test_settings_and_errors(files, monkeypatch, capsys, tmp_path):
    body, _ = files
    monkeypatch.delenv("SMTP_HOST", raising=False)
    base = ["--to", "a@example.com", "--from", "me@example.com", "--subject", "s",
            "--body-file", str(body)]
    assert ers.main([*base, "--send"]) == 1
    assert "no SMTP server" in capsys.readouterr().err
    monkeypatch.delenv("REPORT_FROM", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    assert ers.main(["--to", "a@example.com", "--subject", "s", "--body-file", str(body)]) == 1
    assert "no sender" in capsys.readouterr().err
    assert ers.main([*base[:-1], str(tmp_path / "none.txt")]) == 1
    assert ers.main(["--to", "nope", "--from", "me@example.com", "--subject", "s",
                     "--body-file", str(body)]) == 1
    with pytest.raises(SystemExit):
        ers.main(["--subject", "s", "--body-file", str(body)])


def test_password_comes_from_the_environment_and_is_never_printed(files, monkeypatch, capsys):
    body, _ = files
    monkeypatch.setenv("MY_PW", "s3cret-pw")
    monkeypatch.setenv("SMTP_USER", "mailer")
    seen = {}

    def fake_send(message, recipients, sender, host, port, security, user, password):
        seen.update(user=user, password=password, port=port)

    monkeypatch.setattr(ers, "send", fake_send)
    assert ers.main(["--to", "a@example.com", "--from", "me@example.com", "--subject", "s",
                     "--body-file", str(body), "--smtp-host", "smtp.example.com",
                     "--password-env", "MY_PW", "--send"]) == 0
    assert seen == {"user": "mailer", "password": "s3cret-pw", "port": 587}
    out = capsys.readouterr()
    assert "s3cret-pw" not in out.out + out.err
