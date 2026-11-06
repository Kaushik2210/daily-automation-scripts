import json

import pdf_metadata_viewer as pv
from pypdf import PdfWriter


def make_pdf(path, width=595, height=842, title=None, author=None):
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=height)
    if title or author:
        writer.add_metadata({"/Title": title or "", "/Author": author or ""})
    with path.open("wb") as handle:
        writer.write(handle)


def test_paper_names_in_both_orientations():
    assert pv.paper_name(595, 842) == "A4" and pv.paper_name(842, 595) == "A4"
    assert pv.paper_name(612, 792) == "Letter"
    assert pv.paper_name(300, 300) == "custom"


def test_describe_reads_metadata_and_size(tmp_path):
    make_pdf(tmp_path / "a.pdf", title="My Report", author="Ada")
    info = pv.describe(tmp_path / "a.pdf")
    assert info["pages"] == 1 and info["title"] == "My Report" and info["author"] == "Ada"
    assert info["page_size"] == "210 x 297 mm (A4)" and info["encrypted"] is False


def test_describe_without_metadata(tmp_path):
    make_pdf(tmp_path / "plain.pdf", width=612, height=792)
    info = pv.describe(tmp_path / "plain.pdf")
    assert info["title"] is None and "Letter" in info["page_size"]


def test_cli_text_json_and_bad_file(tmp_path, capsys):
    make_pdf(tmp_path / "a.pdf", title="T")
    (tmp_path / "bad.pdf").write_text("nope")
    assert pv.main([str(tmp_path / "a.pdf")]) == 0
    out = capsys.readouterr().out
    assert out.startswith("a.pdf\n") and "title" in out and "pages" in out
    assert pv.main([str(tmp_path / "a.pdf"), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["pages"] == 1
    assert pv.main([str(tmp_path / "bad.pdf")]) == 1
    assert "can't read it" in capsys.readouterr().err
