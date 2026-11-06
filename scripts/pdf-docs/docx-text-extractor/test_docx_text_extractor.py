import zipfile

import docx_text_extractor as dx

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def p(text, style=None):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p>"


def make_docx(path, body):
    xml = f'<?xml version="1.0"?><w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)


BODY = (p("Agreement", "Title") + p("Terms", "Heading1") + p("Pay within 30 days.")
        + p("Keep it secret", "ListParagraph") + p("   ")
        + "<w:tbl><w:tr><w:tc>" + p("Item") + "</w:tc><w:tc>" + p("Price") + "</w:tc></w:tr>"
        "<w:tr><w:tc>" + p("Consulting") + "</w:tc><w:tc>" + p("$1,200") + "</w:tc></w:tr></w:tbl>")


def test_read_blocks_kinds(tmp_path):
    make_docx(tmp_path / "a.docx", BODY)
    blocks = dx.read_blocks(tmp_path / "a.docx")
    assert [k for k, _ in blocks] == ["h0", "h1", "p", "li", "table"]   # blank paragraph dropped
    assert blocks[-1][1] == [["Item", "Price"], ["Consulting", "$1,200"]]


def test_render_plain_and_markdown(tmp_path):
    make_docx(tmp_path / "a.docx", BODY)
    blocks = dx.read_blocks(tmp_path / "a.docx")
    plain = dx.render(blocks)
    assert "* Keep it secret" in plain and "Item\tPrice" in plain and "#" not in plain
    md = dx.render(blocks, markdown=True)
    assert "# Agreement" in md and "# Terms" in md and "- Keep it secret" in md
    assert "| Item | Price |\n| --- | --- |\n| Consulting | $1,200 |" in md


def test_tabs_and_breaks_inside_a_paragraph(tmp_path):
    body = '<w:p><w:r><w:t>a</w:t><w:tab/><w:t>b</w:t><w:br/><w:t>c</w:t></w:r></w:p>'
    make_docx(tmp_path / "t.docx", body)
    assert dx.read_blocks(tmp_path / "t.docx") == [("p", "a\tb\nc")]


def test_cli_preview_apply_and_errors(tmp_path, capsys):
    make_docx(tmp_path / "a.docx", BODY)
    (tmp_path / "bad.docx").write_text("not a zip")
    assert dx.main([str(tmp_path / "a.docx")]) == 0
    assert "Pay within 30 days." in capsys.readouterr().out
    assert not (tmp_path / "a.txt").exists()
    assert dx.main([str(tmp_path / "a.docx"), "--apply", "--markdown"]) == 0
    assert (tmp_path / "a.md").read_text(encoding="utf-8").startswith("# Agreement")
    assert dx.main([str(tmp_path / "bad.docx")]) == 1
    assert "can't read it as a Word document" in capsys.readouterr().err
