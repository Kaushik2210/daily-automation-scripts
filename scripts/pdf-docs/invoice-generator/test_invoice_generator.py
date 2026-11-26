import json
from decimal import Decimal

import invoice_generator as ig
import pytest

INVOICE = {
    "number": "2026-014", "date": "2026-11-20", "due_date": "2026-12-20", "currency": "USD",
    "from": {"name": "Ada <Studio>", "address": ["1 Way"], "email": "a@example.com"},
    "to": {"name": "Northwind", "address": ["5 Road"]},
    "items": [{"description": "Design", "quantity": 1, "unit_price": 2400},
              {"description": "Revisions", "quantity": 3, "unit_price": 150},
              {"description": "Hosting <hours>", "quantity": 4.5, "unit_price": 80}],
    "tax_rate": 8.5, "discount": 100, "notes": "Pay in 30 days."}


def test_calculate_uses_exact_decimals():
    figures = ig.calculate(INVOICE)
    assert [line["total"] for line in figures["lines"]] == [
        Decimal("2400.00"), Decimal("450.00"), Decimal("360.00")]
    assert figures["subtotal"] == Decimal("3210.00") and figures["discount"] == Decimal("100.00")
    assert figures["tax"] == Decimal("264.35")  # 3110 * 8.5% = 264.35
    assert figures["total"] == Decimal("3374.35")


def test_rounding_is_half_up_per_line():
    data = {**INVOICE, "items": [{"description": "x", "quantity": 3, "unit_price": "0.335"}],
            "tax_rate": 0, "discount": 0}
    assert ig.calculate(data)["lines"][0]["total"] == Decimal("1.01")  # 1.005 rounds up
    assert ig.money("2.675") == Decimal("2.68")


@pytest.mark.parametrize("change,message", [
    ({"number": ""}, "number"), ({"items": []}, "items"), ({"to": None}, "'to'"),
    ({"items": [{"description": "x", "quantity": 0, "unit_price": 5}]}, "quantity"),
    ({"items": [{"description": "x", "unit_price": -1}]}, "price"),
    ({"items": [{"description": "x"}]}, "unit_price"),
    ({"discount": 99999}, "discount"), ({"tax_rate": -5}, "tax_rate"),
    ({"tax_rate": "lots"}, "tax_rate")])
def test_bad_invoices_are_rejected(change, message):
    with pytest.raises(ValueError, match=message):
        ig.calculate({**INVOICE, **change})


def test_formatting():
    assert ig.amount_text(Decimal("1234.5"), "USD") == "$1,234.50"
    assert ig.amount_text(Decimal(9), "CHF") == "9.00 CHF"
    assert [ig.quantity_text(Decimal(v)) for v in ("1", "4.50", "2.25", "10")] == [
        "1", "4.5", "2.25", "10"]


def test_html_is_escaped_complete_and_printable():
    page = ig.render_html(INVOICE, ig.calculate(INVOICE))
    assert "Ada &lt;Studio&gt;" in page and "Hosting &lt;hours&gt;" in page
    assert "<Studio>" not in page
    assert "$3,374.35" in page and "Tax (8.5%)" in page and "Discount" in page
    assert "Due 2026-12-20" in page and "@media print" in page and 'lang="en"' in page
    plain = {**INVOICE, "tax_rate": 0, "discount": 0}
    page = ig.render_html(plain, ig.calculate(plain))
    assert "Tax" not in page and "Discount" not in page


def test_text_summary():
    text = ig.render_text(INVOICE, ig.calculate(INVOICE))
    assert text.splitlines()[0] == "Invoice 2026-014 for Northwind"
    assert "Tax 8.5%" in text and text.rstrip().endswith("$3,374.35")


def test_cli(tmp_path, capsys):
    src = tmp_path / "inv.json"
    src.write_text(json.dumps(INVOICE))
    out = tmp_path / "inv.html"
    assert ig.main([str(src), "--output", str(out)]) == 0
    assert "total $3,374.35" in capsys.readouterr().out
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert ig.main([str(src), "--output", str(out)]) == 1
    assert ig.main([str(src), "--output", str(out), "--force"]) == 0
    capsys.readouterr()
    assert ig.main([str(src), "--format", "text"]) == 0
    assert "TOTAL DUE" in capsys.readouterr().out


def test_cli_errors(tmp_path, capsys):
    assert ig.main([str(tmp_path / "missing.json")]) == 1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({**INVOICE, "items": []}))
    assert ig.main([str(bad)]) == 1
    assert "Can't make the invoice" in capsys.readouterr().err
    bad.write_text("[1, 2]")
    assert ig.main([str(bad)]) == 1
