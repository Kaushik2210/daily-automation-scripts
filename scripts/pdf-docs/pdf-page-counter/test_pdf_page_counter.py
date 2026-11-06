import pdf_page_counter as pc
import pytest
from pypdf import PdfWriter


def make_pdf(path, pages, password=None):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    if password:
        writer.encrypt(password, algorithm="RC4-128")
    with path.open("wb") as handle:
        writer.write(handle)


def test_count_pages_and_errors(tmp_path):
    make_pdf(tmp_path / "a.pdf", 3)
    assert pc.count_pages(tmp_path / "a.pdf") == 3
    (tmp_path / "bad.pdf").write_text("nope")
    with pytest.raises(ValueError, match="not a readable PDF"):
        pc.count_pages(tmp_path / "bad.pdf")
    make_pdf(tmp_path / "locked.pdf", 1, password="secret")
    with pytest.raises(ValueError, match="password protected"):
        pc.count_pages(tmp_path / "locked.pdf")


def test_find_pdfs_recursive_and_case(tmp_path):
    (tmp_path / "sub").mkdir()
    make_pdf(tmp_path / "a.pdf", 1)
    make_pdf(tmp_path / "sub" / "B.PDF", 1)
    (tmp_path / "notes.txt").write_text("x")
    assert [p.name for p in pc.find_pdfs([tmp_path])] == ["a.pdf"]
    assert [p.name for p in pc.find_pdfs([tmp_path], recursive=True)] == ["B.PDF", "a.pdf"] or \
        sorted(p.name for p in pc.find_pdfs([tmp_path], recursive=True)) == ["B.PDF", "a.pdf"]


def test_cli_totals_and_skips(tmp_path, capsys):
    make_pdf(tmp_path / "a.pdf", 2)
    make_pdf(tmp_path / "b.pdf", 5)
    (tmp_path / "bad.pdf").write_text("nope")
    assert pc.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "2 PDF(s), 7 page(s) in total, 1 skipped." in out
    assert "bad.pdf" in out and "skipped:" in out


def test_clean_run_exit_code(tmp_path, capsys):
    make_pdf(tmp_path / "a.pdf", 4)
    assert pc.main([str(tmp_path / "a.pdf")]) == 0
    assert "1 PDF(s), 4 page(s) in total." in capsys.readouterr().out
    assert pc.human_size(2048) == "2.0 KB"
