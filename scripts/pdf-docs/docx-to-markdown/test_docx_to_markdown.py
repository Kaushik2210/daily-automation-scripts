import zipfile

import docx_to_markdown as d2m

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def run(text, bold=False, italic=False):
    props = ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "")
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{text}</w:t></w:r>'


def para(content, style=None, num=None):
    ppr = ""
    if style:
        ppr += f'<w:pStyle w:val="{style}"/>'
    if num:
        ppr += f'<w:numPr><w:ilvl w:val="{num[1]}"/><w:numId w:val="{num[0]}"/></w:numPr>'
    return f"<w:p><w:pPr>{ppr}</w:pPr>{content}</w:p>" if ppr else f"<w:p>{content}</w:p>"


def make_docx(path, body, rels="", numbering=""):
    document = f'<?xml version="1.0"?><w:document {NS}><w:body>{body}</w:body></w:document>'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", document)
        if rels:
            z.writestr("word/_rels/document.xml.rels",
                       f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
                       f'relationships">{rels}</Relationships>')
        if numbering:
            z.writestr("word/numbering.xml", f'<w:numbering {NS}>{numbering}</w:numbering>')
    return path


def test_headings_bold_italic_and_title(tmp_path):
    body = (para(run("Report"), "Title") + para(run("Intro"), "Heading1")
            + para(run("Sub"), "Heading2")
            + para(run("Plain ") + run("bold", bold=True) + run(" and ") + run("it", italic=True)))
    markdown = d2m.convert(make_docx(tmp_path / "a.docx", body))
    assert markdown == "# Report\n\n## Intro\n\n### Sub\n\nPlain **bold** and *it*\n"


def test_without_title_headings_keep_their_level(tmp_path):
    markdown = d2m.convert(make_docx(tmp_path / "a.docx", para(run("Top"), "Heading1")))
    assert markdown == "# Top\n"


def test_neighbouring_runs_merge_and_spaces_stay_outside_markers(tmp_path):
    body = para(run("one ", bold=True) + run("two", bold=True) + run(" three"))
    assert d2m.convert(make_docx(tmp_path / "a.docx", body)) == "**one two** three\n"


def test_hyperlinks(tmp_path):
    link = '<w:hyperlink r:id="rId5">' + run("our site") + "</w:hyperlink>"
    rels = ('<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/hyperlink" Target="https://example.com" TargetMode="External"/>')
    markdown = d2m.convert(make_docx(tmp_path / "a.docx", para(run("Visit ") + link), rels=rels))
    assert markdown == "Visit [our site](https://example.com)\n"


def test_bullet_and_numbered_lists_from_numbering_xml(tmp_path):
    numbering = ('<w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/>'
                 '</w:lvl></w:abstractNum><w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0">'
                 '<w:numFmt w:val="decimal"/></w:lvl></w:abstractNum>'
                 '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
                 '<w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num>')
    body = (para(run("Before")) + para(run("a"), num=("1", 0)) + para(run("b"), num=("1", 1))
            + para(run("x"), num=("2", 0)) + para(run("y"), num=("2", 0)) + para(run("After")))
    markdown = d2m.convert(make_docx(tmp_path / "a.docx", body, numbering=numbering))
    assert markdown == "Before\n\n- a\n  - b\n1. x\n2. y\n\nAfter\n"


def test_list_styles_without_numbering_xml(tmp_path):
    body = (para(run("a"), "ListBullet") + para(run("b"), "ListBullet")
            + para(run("one"), "ListNumber") + para(run("two"), "ListNumber"))
    assert d2m.convert(make_docx(tmp_path / "a.docx", body)) == "- a\n- b\n1. one\n2. two\n"


def test_tables(tmp_path):
    def cell(text):
        return f"<w:tc>{para(run(text))}</w:tc>"
    table = ("<w:tbl><w:tr>" + cell("Name") + cell("Qty") + "</w:tr><w:tr>" + cell("a|b")
             + cell("2") + "</w:tr></w:tbl>")
    assert d2m.convert(make_docx(tmp_path / "a.docx", table)) == (
        "| Name | Qty |\n| --- | --- |\n| a\\|b | 2 |\n")


def test_cli_prints_writes_and_reports_errors(tmp_path, capsys):
    good = make_docx(tmp_path / "good.docx", para(run("Hello")))
    bad = tmp_path / "bad.docx"
    bad.write_text("not a zip")
    assert d2m.main([str(good)]) == 0
    assert capsys.readouterr().out == "Hello\n"
    out_dir = tmp_path / "md"
    assert d2m.main([str(good), "-o", str(out_dir)]) == 0
    assert (out_dir / "good.md").read_text() == "Hello\n"
    d2m.main([str(good), "-o", str(out_dir)])
    assert "already exists" in capsys.readouterr().out
    assert d2m.main([str(bad)]) == 1
    assert "can't read it" in capsys.readouterr().err
