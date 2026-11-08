import csv
from datetime import datetime

import price_tracker as pt
import pytest


@pytest.mark.parametrize("text,expected", [
    ("79.99", 79.99), ("$1,299.00", 1299.0), ("1.299,00", 1299.0), ("5,50", 5.5),
    ("1,299", 1299.0), ("EUR 12", 12.0), ("free", None), ("", None)])
def test_parse_amount(text, expected):
    assert pt.parse_amount(text) == expected


def test_structured_data_is_preferred():
    html = ('<script type="application/ld+json">{"@type":"Product","offers":'
            '{"price":"49.50","priceCurrency":"EUR"}}</script><p>$99</p>')
    assert pt.extract_price(html) == (49.5, "EUR", "structured data")


def test_meta_itemprop_regex_and_page_fallbacks():
    meta = ('<meta property="product:price:amount" content="12.30">'
            '<meta property="product:price:currency" content="GBP">')
    assert pt.extract_price(meta) == (12.3, "GBP", "meta tag")
    assert pt.extract_price('<span itemprop="price">8,99</span>')[::2] == (8.99, "itemprop")
    assert pt.extract_price("Now only 42.00 today", r"only ([\d.]+)") == (
        42.0, "", "your pattern")
    assert pt.extract_price("<style>.x{}</style><b>Sale £3.50.</b>") == (
        3.5, "GBP", "first price on page")
    assert pt.extract_price("<p>no price here</p>") is None


def test_describe_drop_rise_unchanged_and_target():
    history = [("2026-01-01 09:00:00", 100.0), ("2026-02-01 09:00:00", 90.0)]
    drop = pt.describe(80.0, "USD", history, target=85)
    assert drop[1].startswith("PRICE DROP: 10.00 less than 90.00 on 2026-02-01 (11.1%)")
    assert drop[2] == "Lowest price seen so far!" and drop[3].startswith("At or below")
    assert "rose by 20.00" in pt.describe(110.0, "USD", history)[1]
    assert pt.describe(90.0, "", history)[1] == "Unchanged since 2026-02-01."
    assert pt.describe(5.0, "", [])[1] == "First reading for this page."


def test_history_roundtrip_ignores_other_urls(tmp_path):
    log = tmp_path / "prices.csv"
    pt.record(log, "a.html", 10.0, "USD", datetime(2026, 3, 1, 8, 0, 0))
    pt.record(log, "b.html", 99.0, "USD", datetime(2026, 3, 1, 8, 0, 0))
    pt.record(log, "a.html", 9.0, "USD", datetime(2026, 3, 2, 8, 0, 0))
    assert next(csv.reader(log.open())) == pt.HEADER
    assert pt.read_history(log, "a.html") == [("2026-03-01 08:00:00", 10.0),
                                              ("2026-03-02 08:00:00", 9.0)]
    assert pt.read_history(tmp_path / "missing.csv", "a.html") == []


def test_cli_records_and_flags_a_drop(tmp_path, capsys):
    page, log = tmp_path / "p.html", tmp_path / "h.csv"
    page.write_text('<meta property="og:price:amount" content="20.00">')
    assert pt.main([str(page), "--history", str(log)]) == 0
    assert "First reading" in capsys.readouterr().out
    page.write_text('<meta property="og:price:amount" content="15.00">')
    assert pt.main([str(page), "--history", str(log), "--no-record", "--target", "16"]) == 0
    out = capsys.readouterr().out
    assert "PRICE DROP: 5.00" in out and "At or below your target" in out
    assert len(log.read_text().splitlines()) == 2  # header + the first reading only


def test_cli_without_a_price_fails(tmp_path, capsys):
    page = tmp_path / "p.html"
    page.write_text("<p>nothing</p>")
    assert pt.main([str(page)]) == 1
    assert "Couldn't find a price" in capsys.readouterr().out
