import invoice_renamer as ir

ACME = "ACME Supplies Ltd\nInvoice No: INV-1042\nDate: 2026-01-15\nTotal: $230.50"
BLUE = "Blue Sky Hosting\nInvoice Number: BS-7781\nInvoice date: 12/02/2026\nAmount due: 89.00"


def test_find_date_formats():
    assert ir.find_date("Date: 2026-01-15") == "2026-01-15"
    assert ir.find_date("on 12/02/2026") == "2026-02-12"
    assert ir.find_date("on 12/02/2026", dayfirst=False) == "2026-12-02"
    assert ir.find_date("Issued March 4, 2026") == "2026-03-04"
    assert ir.find_date("Issued 4 Mar 2026") == "2026-03-04"
    assert ir.find_date("31/31/2026") is None and ir.find_date("no date") is None


def test_parse_invoice():
    assert ir.parse_invoice(ACME) == {"date": "2026-01-15", "vendor": "ACME Supplies Ltd",
                                      "number": "INV-1042"}
    assert ir.parse_invoice(BLUE)["number"] == "BS-7781"
    assert ir.parse_invoice("")["vendor"] is None


def test_new_name_patterns_and_missing_parts():
    info = ir.parse_invoice(ACME)
    assert ir.new_name(info) == "2026-01-15_ACME-Supplies-Ltd_INV-1042.pdf"
    assert ir.new_name(info, "{vendor}_{date}") == "ACME-Supplies-Ltd_2026-01-15.pdf"
    undated = {"date": None, "vendor": "X", "number": "1"}
    assert ir.new_name(undated) is None
    assert ir.new_name(undated, "{vendor}-{number}") == "X-1.pdf"


def test_cli_dry_run_and_apply_with_real_pdfs(tmp_path, capsys, monkeypatch):
    for name in ("scan_1.pdf", "scan_2.pdf", "junk.pdf"):
        (tmp_path / name).write_bytes(b"%PDF placeholder")
    texts = {"scan_1.pdf": ACME, "scan_2.pdf": BLUE, "junk.pdf": "nothing useful"}
    monkeypatch.setattr(ir, "read_text", lambda path: texts[path.name])
    assert ir.main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "scan_1.pdf -> 2026-01-15_ACME-Supplies-Ltd_INV-1042.pdf" in out
    assert "scan_2.pdf -> 2026-02-12_Blue-Sky-Hosting_BS-7781.pdf" in out
    assert "skip junk.pdf" in out and (tmp_path / "scan_1.pdf").exists()
    ir.main([str(tmp_path), "--apply"])
    assert (tmp_path / "2026-02-12_Blue-Sky-Hosting_BS-7781.pdf").exists()
    assert not (tmp_path / "scan_1.pdf").exists() and (tmp_path / "junk.pdf").exists()


def test_unreadable_pdf_is_skipped(tmp_path, capsys):
    (tmp_path / "bad.pdf").write_text("not a pdf")
    ir.main([str(tmp_path)])
    assert "skip bad.pdf: can't read it" in capsys.readouterr().out
