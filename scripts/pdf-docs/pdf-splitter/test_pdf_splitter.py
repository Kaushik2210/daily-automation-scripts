import pdf_splitter as ps
import pytest
from pypdf import PdfReader, PdfWriter


def make_pdf(path, pages):
    writer = PdfWriter()
    for i in range(pages):
        writer.add_blank_page(width=100 + i, height=200)   # width marks the page number
    with path.open("wb") as handle:
        writer.write(handle)


def test_parse_ranges():
    assert ps.parse_ranges("1-3,5", 10) == [1, 2, 3, 5]
    assert ps.parse_ranges("8-", 10) == [8, 9, 10]
    assert ps.parse_ranges("-2", 10) == [1, 2]
    for bad in ("0", "11", "3-1", "x", ""):
        with pytest.raises(ValueError):
            ps.parse_ranges(bad, 10)


def test_plan_pages_and_chunks():
    assert ps.plan(10, pages_text="1-3,5") == [("_pages_1-3_5", [1, 2, 3, 5])]
    chunks = ps.plan(5, every=2)
    assert [pages for _, pages in chunks] == [[1, 2], [3, 4], [5]]
    assert chunks[0][0] == "_part001"
    assert len(ps.plan(3, every=1)) == 3


def test_apply_extracts_the_right_pages(tmp_path):
    src = tmp_path / "book.pdf"
    make_pdf(src, 6)
    assert ps.main([str(src), "--pages", "2,4-5", "-o", str(tmp_path / "out"), "--apply"]) == 0
    reader = PdfReader(str(tmp_path / "out" / "book_pages_2_4-5.pdf"))
    assert [int(p.mediabox.width) for p in reader.pages] == [101, 103, 104]


def test_every_dry_run_then_apply(tmp_path, capsys):
    src = tmp_path / "book.pdf"
    make_pdf(src, 5)
    ps.main([str(src), "--every", "2"])
    assert "Would write 3 file(s)." in capsys.readouterr().out
    assert not list(tmp_path.glob("book_part*"))
    ps.main([str(src), "--every", "2", "--apply"])
    assert len(PdfReader(str(tmp_path / "book_part003.pdf")).pages) == 1


def test_argument_errors_and_bad_pdf(tmp_path, capsys):
    src = tmp_path / "book.pdf"
    make_pdf(src, 2)
    with pytest.raises(SystemExit):
        ps.main([str(src)])
    with pytest.raises(SystemExit):
        ps.main([str(src), "--pages", "1", "--every", "1"])
    with pytest.raises(SystemExit):
        ps.main([str(src), "--pages", "9"])
    bad = tmp_path / "bad.pdf"
    bad.write_text("nope")
    assert ps.main([str(bad), "--every", "1"]) == 1
    assert "Can't read bad.pdf" in capsys.readouterr().err
