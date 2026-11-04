from datetime import date

import pytest
import weekly_planner as wp


def test_week_helpers():
    assert wp.next_monday(date(2026, 1, 5)) == date(2026, 1, 5)    # already Monday
    assert wp.next_monday(date(2026, 1, 8)) == date(2026, 1, 12)   # Thursday
    assert wp.monday_of(date(2026, 1, 8)) == date(2026, 1, 5)


def test_planner_structure_weekdays():
    text = wp.build_planner(date(2026, 1, 5), ["Ship it", "Gym x3"])
    assert text.startswith("# Week of 05 Jan 2026\n*05 Jan to 09 Jan*")
    assert "- [ ] Ship it" in text and "- [ ] Gym x3" in text
    assert text.count("## ") == 1 + 5 + 1  # goals + five days + review
    assert "## Saturday" not in text and "## Monday 05 Jan" in text


def test_weekend_and_slots_and_empty_goals():
    text = wp.build_planner(date(2026, 1, 5), weekend=True, slots=2)
    assert "## Sunday 11 Jan" in text
    day_block = text.split("## Monday 05 Jan\n")[1].split("\n\n")[0]
    assert day_block.count("- [ ]") == 2
    assert text.split("## Goals\n")[1].startswith("- [ ] \n")


def test_cli_preview_then_apply_and_no_overwrite(tmp_path, capsys):
    out = tmp_path / "plan.md"
    wp.main(["--week-of", "2026-01-07", "-o", str(out)])
    assert not out.exists() and "# Week of 05 Jan 2026" in capsys.readouterr().out
    assert wp.main(["--week-of", "2026-01-07", "-o", str(out), "--apply"]) == 0
    assert out.read_text(encoding="utf-8").startswith("# Week of 05 Jan 2026")
    assert wp.main(["--week-of", "2026-01-07", "-o", str(out), "--apply"]) == 1


def test_bad_date():
    with pytest.raises(SystemExit):
        wp.main(["--week-of", "5th January"])
