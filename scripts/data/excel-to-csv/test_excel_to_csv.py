from datetime import date

import pytest
from excel_to_csv import cell_text, main, safe_name
from openpyxl import Workbook


def make_workbook(path):
    wb = Workbook()
    first = wb.active
    first.title = "Sales 2026"
    first.append(["item", "qty", "day"])
    first.append(["pen", 3.0, date(2026, 1, 5)])
    first.append(["ink", 2.5, None])
    second = wb.create_sheet("Notes")
    second.append(["hello"])
    wb.save(path)


def test_cell_text_and_safe_name():
    assert cell_text(None) == "" and cell_text(4.0) == "4" and cell_text(2.5) == "2.5"
    assert cell_text(date(2026, 1, 5)) == "2026-01-05"
    assert safe_name("Sales 2026/Q1") == "Sales_2026_Q1"


def test_dry_run_lists_sheets_without_writing(tmp_path, capsys):
    book = tmp_path / "book.xlsx"
    make_workbook(book)
    main([str(book)])
    assert "Sales 2026: 3 row(s)" in capsys.readouterr().out
    assert not list(tmp_path.glob("*.csv"))


def test_apply_writes_each_sheet(tmp_path):
    book = tmp_path / "book.xlsx"
    make_workbook(book)
    main([str(book), "--apply"])
    sales = (tmp_path / "book_Sales_2026.csv").read_text().splitlines()
    assert sales == ["item,qty,day", "pen,3,2026-01-05", "ink,2.5,"]
    assert (tmp_path / "book_Notes.csv").read_text().strip() == "hello"


def test_unknown_sheet_is_an_error(tmp_path):
    book = tmp_path / "book.xlsx"
    make_workbook(book)
    with pytest.raises(SystemExit):
        main([str(book), "--sheet", "Nope"])
