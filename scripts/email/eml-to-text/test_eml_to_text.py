from email.message import EmailMessage

import eml_to_text as et


def make(subject="Hello", plain="Plain body", html=None, attach=None):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = "Ann <a@x.test>", "Bob <b@x.test>", subject
    msg["Date"] = "Mon, 05 Oct 2026 09:00:00 +0000"
    if plain is not None:
        msg.set_content(plain)
        if html:
            msg.add_alternative(html, subtype="html")
    else:
        msg.set_content(html, subtype="html")
    if attach:
        msg.add_attachment(b"data", maintype="application", subtype="pdf", filename=attach)
    return msg.as_bytes()


def test_html_to_text_handles_lists_links_and_skips_scripts():
    html = ("<html><head><title>T</title><style>p{}</style></head><body><h1>Hi</h1>"
            "<p>See <a href='https://x.test/a'>this page</a> &amp; more.</p>"
            "<ul><li>one</li><li>two</li></ul><script>bad()</script></body></html>")
    assert et.html_to_text(html) == (
        "Hi\n\nSee this page (https://x.test/a) & more.\n\n- one\n- two")


def test_plain_text_is_preferred_and_headers_are_listed():
    text = et.convert(make(html="<p>HTML body</p>"))
    assert text.startswith("From: Ann <a@x.test>\nTo: Bob <b@x.test>\nDate: Mon, 05 Oct 2026")
    assert "Subject: Hello\n\nPlain body" in text and "HTML body" not in text


def test_html_only_mail_is_converted():
    text = et.convert(make(plain=None, html="<p>Only <b>html</b> here</p>"))
    assert text.endswith("Only html here\n")


def test_attachments_are_listed_and_wrapping_works():
    text = et.convert(make(plain="word " * 40, attach="report.pdf"), width=30)
    assert text.rstrip().endswith("Attachments: report.pdf")
    body = text.split("\n\n", 1)[1].split("\n\nAttachments")[0]
    assert max(len(line) for line in body.splitlines()) <= 30


def test_empty_message():
    msg = EmailMessage()
    msg["Subject"] = "Nothing"
    assert "(no text in this message)" in et.convert(msg.as_bytes())


def test_stdout_mode_for_one_and_many_files(tmp_path, capsys):
    one, two = tmp_path / "one.eml", tmp_path / "two.eml"
    one.write_bytes(make("First"))
    two.write_bytes(make("Second"))
    assert et.main([str(one)]) == 0
    assert capsys.readouterr().out.startswith("From: Ann")
    assert et.main([str(tmp_path)]) == 0  # a folder is searched for .eml files
    out = capsys.readouterr().out
    assert "===== one.eml =====" in out and "===== two.eml =====" in out


def test_dry_run_then_apply_never_overwrites(tmp_path, capsys):
    src, out = tmp_path / "msg.eml", tmp_path / "out"
    src.write_bytes(make())
    assert et.main([str(src), "--out-dir", str(out)]) == 0
    assert "Dry run" in capsys.readouterr().out and not out.exists()
    assert et.main([str(src), "--out-dir", str(out), "--apply"]) == 0
    assert (out / "msg.txt").read_text().startswith("From: Ann")
    (out / "msg.txt").write_text("keep me")
    assert et.main([str(src), "--out-dir", str(out), "--apply"]) == 0
    assert (out / "msg.txt").read_text() == "keep me" and (out / "msg-2.txt").exists()


def test_missing_input(tmp_path, capsys):
    assert et.main([str(tmp_path)]) == 1  # an empty folder has no .eml files
    assert et.main([str(tmp_path / "gone.eml")]) == 1
    assert "couldn't read" in capsys.readouterr().out
