from decimal import Decimal

import expense_logger as ex
import pytest


def test_parse_amount_formats_and_errors():
    assert ex.parse_amount("4.5") == Decimal("4.50")
    assert ex.parse_amount("$1,234.567") == Decimal("1234.57")
    with pytest.raises(ValueError):
        ex.parse_amount("abc")
    with pytest.raises(ValueError):
        ex.parse_amount("-3")


def test_totals_use_exact_decimals():
    rows = [{"amount": "0.10", "category": "a"}, {"amount": "0.20", "category": "a"},
            {"amount": "5.00", "category": "b"}]
    by_category, grand = ex.totals(rows)
    assert by_category == {"b": Decimal("5.00"), "a": Decimal("0.30")}
    assert grand == Decimal("5.30")


def test_in_month_filter():
    rows = [{"date": "2026-01-02"}, {"date": "2026-02-01"}]
    assert ex.in_month(rows, "2026-02") == [{"date": "2026-02-01"}]
    assert ex.in_month(rows, None) == rows


def test_cli_add_list_summary(tmp_path, capsys):
    f = str(tmp_path / "e.csv")
    ex.main(["add", "4.50", "Coffee", "flat", "white", "--date", "2026-01-02", "--file", f])
    ex.main(["add", "60", "groceries", "--date", "2026-01-03", "--file", f])
    ex.main(["add", "900", "rent", "--date", "2026-02-01", "--file", f])
    capsys.readouterr()
    ex.main(["list", "--month", "2026-01", "--file", f])
    out = capsys.readouterr().out
    assert "flat white" in out and "rent" not in out and "2 expense(s)." in out
    ex.main(["summary", "--file", f])
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("rent") and "964.50" in out


def test_empty_and_bad_input(tmp_path, capsys):
    f = str(tmp_path / "none.csv")
    assert ex.main(["summary", "--file", f]) == 0
    assert "No expenses found." in capsys.readouterr().out
    with pytest.raises(SystemExit):
        ex.main(["add", "5", "--file", f])
    with pytest.raises(SystemExit):
        ex.main(["add", "five", "food", "--file", f])
