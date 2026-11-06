import pdf_text_extractor as pt
from pypdf import PdfWriter


def blank_pdf(path, pages=1):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    with path.open("wb") as handle:
        writer.write(handle)


def text_pdf(path, pages):
    """A tiny valid PDF where page N says 'Hello from page N'."""
    objs = {1: "<< /Type /Catalog /Pages 2 0 R >>",
            2: f"<< /Type /Pages /Kids [{' '.join(f'{4 + 2 * i} 0 R' for i in range(pages))}] "
               f"/Count {pages} >>",
            3: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"}
    for i in range(pages):
        pid = 4 + 2 * i
        stream = f"BT /F1 14 Tf 72 700 Td (Hello from page {i + 1}) Tj ET"
        objs[pid] = ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
                     f"/Contents {pid + 1} 0 R /Resources << /Font << /F1 3 0 R >> >> >>")
        objs[pid + 1] = f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"
    out, offsets = bytearray(b"%PDF-1.4\n"), {}
    for n in sorted(objs):
        offsets[n] = len(out)
        out += f"{n} 0 obj\n{objs[n]}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {max(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{offsets[n]:010d} 00000 n \n".encode() for n in range(1, max(objs) + 1))
    out += f"trailer\n<< /Size {max(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


def test_extract_text_and_markers(tmp_path):
    text_pdf(tmp_path / "t.pdf", 2)
    text, pages = pt.extract(tmp_path / "t.pdf")
    assert pages == 2 and text == "Hello from page 1\n\nHello from page 2"
    marked, _ = pt.extract(tmp_path / "t.pdf", markers=True)
    assert marked.startswith("--- page 1 ---\nHello from page 1")


def test_preview_truncates():
    assert pt.preview("abcdef", 3) == "abc\n... (3 more characters)"
    assert pt.preview("abcdef", 0) == "abcdef"


def test_scanned_pdf_has_no_text_message(tmp_path, capsys):
    blank_pdf(tmp_path / "scan.pdf")
    assert pt.main([str(tmp_path / "scan.pdf")]) == 0
    assert "no text found" in capsys.readouterr().out


def test_preview_then_apply_writes_txt(tmp_path, capsys):
    text_pdf(tmp_path / "t.pdf", 1)
    pt.main([str(tmp_path / "t.pdf")])
    out = capsys.readouterr().out
    assert "Hello from page 1" in out and not (tmp_path / "t.txt").exists()
    pt.main([str(tmp_path / "t.pdf"), "--apply", "-o", str(tmp_path / "txt")])
    assert (tmp_path / "txt" / "t.txt").read_text(encoding="utf-8") == "Hello from page 1\n"


def test_unreadable_file_sets_exit_code(tmp_path, capsys):
    (tmp_path / "bad.pdf").write_text("nope")
    assert pt.main([str(tmp_path / "bad.pdf")]) == 1
    assert "can't read it" in capsys.readouterr().err
