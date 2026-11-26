import json
from decimal import Decimal

import expense_summary as es
import pytest

CSV = """date,amount,category,note
2026-10-01,900.00,Rent,october rent
2026-10-05,50.50,groceries,shop
2026-11-01,900.00,rent,november rent
2026-11-03,"1,020.10",groceries,big shop
2026-11-04,4.50,coffee,
2026-11-09,oops,fun,broken
2026-11-10,12.00,,no category
not-a-date,5,fun,x
"""


@pytest.fixture
def path(tmp_path):
    file = tmp_path / "e.csv"
    file.write_text(CSV, encoding="utf-8")
    return file


def test_read_expenses_cleans_rows_and_reports_problems(path):
    rows, problems = es.read_expenses(path)
    assert len(rows) == 6 and len(problems) == 2
    assert rows[0]["category"] == "rent" and rows[3]["amount"] == Decimal("1020.10")
    assert rows[-1]["category"] == "uncategorised"
    assert problems[0].startswith("line 7") and "oops" in problems[0]


def test_read_expenses_needs_columns(tmp_path):
    bad = tmp_path / "b.csv"
    bad.write_text("when,cost\n1,2\n")
    with pytest.raises(ValueError):
        es.read_expenses(bad)


def test_previous_month_wraps_the_year():
    assert es.previous_month("2026-11") == "2026-10" and es.previous_month("2026-01") == "2025-12"


def test_parse_budgets():
    assert es.parse_budgets(["Food=300", "eating out=50.5"]) == {
        "food": Decimal(300), "eating out": Decimal("50.5")}
    for bad in ("food", "=5", "food=lots"):
        with pytest.raises(ValueError):
            es.parse_budgets([bad])


def test_summarise_totals_changes_and_budgets(path):
    rows, _ = es.read_expenses(path)
    s = es.summarise(rows, "2026-11", es.parse_budgets(["groceries=1000", "coffee=10"]), 2)
    assert s["total"] == Decimal("1936.60") and s["entries"] == 4
    assert [c["name"] for c in s["categories"]] == ["groceries", "rent", "uncategorised", "coffee"]
    groceries = s["categories"][0]
    assert groceries["change"] == Decimal("969.60") and round(groceries["share"]) == 53
    assert s["previous_total"] == Decimal("950.50") and s["daily_average"] == Decimal("64.55")
    assert [b["over"] for b in s["budgets"]] == [Decimal("20.10"), Decimal("-5.50")]
    assert [r["amount"] for r in s["top"]] == [Decimal("1020.10"), Decimal("900.00")]
    assert es.summarise(rows, "2025-01", {}, 3) is None
    first = es.summarise(rows, "2026-10", {}, 3)
    assert first["previous_total"] is None and first["categories"][0]["change"] is None


def test_cli_text_markdown_json(path, capsys):
    assert es.main([str(path), "--budget", "groceries=1000", "--budget", "coffee=10"]) == 0
    out = capsys.readouterr()
    assert "Expenses for 2026-11 (4 entries)" in out.out and "vs 2026-10" in out.out
    assert "groceries: 1,020.10 of 1,000.00 (OVER by 20.10)" in out.out
    assert "coffee: 4.50 of 10.00 (5.50 left)" in out.out and "Skipped line 7" in out.err
    assert es.main([str(path), "--month", "2026-10", "--format", "markdown"]) == 0
    md = capsys.readouterr().out
    assert md.startswith("## Expenses for 2026-10") and "| **Total** | 950.50 | 100% |" in md
    assert "Change" not in md  # no month before October, so no comparison column
    assert es.main([str(path), "--format", "json", "--top", "1"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["total"] == "1936.60" and data["top"][0]["date"] == "2026-11-03"


def test_cli_errors(path, tmp_path, capsys):
    assert es.main([str(path), "--month", "2020-01"]) == 1
    assert "No expenses found for 2020-01" in capsys.readouterr().err
    assert es.main([str(tmp_path / "missing.csv")]) == 1
    empty = tmp_path / "e.csv"
    empty.write_text("date,amount,category\n")
    assert es.main([str(empty)]) == 1
    for argv in (["--month", "soon"], ["--budget", "x"], ["--top", "-1"]):
        with pytest.raises(SystemExit):
            es.main([str(path), *argv])
