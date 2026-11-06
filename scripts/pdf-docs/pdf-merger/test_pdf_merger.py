import pdf_merger as pm
from pypdf import PdfReader, PdfWriter


def make_pdf(path, pages, width=200):
    writer = PdfWriter()
    for i in range(pages):
        writer.add_blank_page(width=width + i, height=300)
    with path.open("wb") as handle:
        writer.write(handle)


def test_page_counts_and_bad_file(tmp_path):
    make_pdf(tmp_path / "a.pdf", 2)
    (tmp_path / "bad.pdf").write_text("not a pdf")
    assert pm.page_counts([tmp_path / "a.pdf"]) == [(tmp_path / "a.pdf", 2)]
    try:
        pm.page_counts([tmp_path / "bad.pdf"])
    except ValueError as err:
        assert "bad.pdf isn't a readable PDF" in str(err)
    else:
        raise AssertionError("expected ValueError")


def test_merge_keeps_order_and_bookmarks(tmp_path):
    make_pdf(tmp_path / "a.pdf", 2, width=100)
    make_pdf(tmp_path / "b.pdf", 1, width=500)
    out = tmp_path / "out.pdf"
    with out.open("wb") as handle:
        pm.merge([tmp_path / "b.pdf", tmp_path / "a.pdf"], bookmarks=True).write(handle)
    reader = PdfReader(str(out))
    assert [int(p.mediabox.width) for p in reader.pages] == [500, 100, 101]
    assert [item.title for item in reader.outline] == ["b", "a"]


def test_cli_dry_run_apply_and_no_overwrite(tmp_path, capsys):
    make_pdf(tmp_path / "a.pdf", 2)
    make_pdf(tmp_path / "b.pdf", 3)
    out = tmp_path / "merged.pdf"
    args = [str(tmp_path / "a.pdf"), str(tmp_path / "b.pdf"), "-o", str(out)]
    assert pm.main(args) == 0 and not out.exists()
    text = capsys.readouterr().out
    assert "would write" in text and "with 5 page(s)" in text
    assert pm.main([*args, "--apply"]) == 0
    assert len(PdfReader(str(out)).pages) == 5
    assert pm.main([*args, "--apply"]) == 1


def test_unreadable_input_stops(tmp_path):
    (tmp_path / "bad.pdf").write_text("nope")
    make_pdf(tmp_path / "a.pdf", 1)
    assert pm.main([str(tmp_path / "a.pdf"), str(tmp_path / "bad.pdf")]) == 1
