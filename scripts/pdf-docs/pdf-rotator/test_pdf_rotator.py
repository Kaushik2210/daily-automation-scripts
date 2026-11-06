import pdf_rotator as pr
import pytest
from pypdf import PdfReader, PdfWriter


def make_pdf(path, pages):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=200)
    with path.open("wb") as handle:
        writer.write(handle)


def test_parse_ranges():
    assert pr.parse_ranges("1-2,4", 5) == [1, 2, 4]
    assert pr.parse_ranges("3-", 5) == [3, 4, 5]
    for bad in ("0", "6", "2-1", "a"):
        with pytest.raises(ValueError):
            pr.parse_ranges(bad, 5)


def test_rotate_only_selected_pages(tmp_path):
    make_pdf(tmp_path / "a.pdf", 3)
    writer = pr.rotate(PdfReader(str(tmp_path / "a.pdf")), 90, [2])
    out = tmp_path / "out.pdf"
    with out.open("wb") as handle:
        writer.write(handle)
    assert [p.rotation for p in PdfReader(str(out)).pages] == [0, 90, 0]


def test_rotation_adds_up(tmp_path):
    make_pdf(tmp_path / "a.pdf", 1)
    once = pr.rotate(PdfReader(str(tmp_path / "a.pdf")), 270, [1])
    out = tmp_path / "b.pdf"
    with out.open("wb") as handle:
        once.write(handle)
    twice = pr.rotate(PdfReader(str(out)), 180, [1])
    out2 = tmp_path / "c.pdf"
    with out2.open("wb") as handle:
        twice.write(handle)
    assert PdfReader(str(out2)).pages[0].rotation == 90   # 270 + 180 = 450 -> 90


def test_cli_dry_run_apply_and_no_overwrite(tmp_path, capsys):
    src = tmp_path / "a.pdf"
    make_pdf(src, 2)
    assert pr.main([str(src), "--angle", "90"]) == 0
    assert "rotate 2 of 2 page(s) by 90 degrees" in capsys.readouterr().out
    assert not (tmp_path / "a_rotated.pdf").exists()
    assert pr.main([str(src), "--angle", "90", "--pages", "1", "--apply"]) == 0
    assert [p.rotation for p in PdfReader(str(tmp_path / "a_rotated.pdf")).pages] == [90, 0]
    assert pr.main([str(src), "--angle", "90", "--apply"]) == 1


def test_bad_input(tmp_path):
    src = tmp_path / "a.pdf"
    make_pdf(src, 1)
    with pytest.raises(SystemExit):
        pr.main([str(src), "--angle", "45"])
    with pytest.raises(SystemExit):
        pr.main([str(src), "--angle", "90", "--pages", "5"])
    (tmp_path / "bad.pdf").write_text("nope")
    assert pr.main([str(tmp_path / "bad.pdf"), "--angle", "90"]) == 1
