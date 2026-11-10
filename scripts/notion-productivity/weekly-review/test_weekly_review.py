import json
from datetime import date

import pytest
import weekly_review as wr

MONDAY = date(2026, 1, 5)
JOURNAL = """# Journal

## 2026-01-04

- 20:00 Sunday before the week

## 2026-01-05

- 09:10 Started with a walk.
- 18:45 Sent the draft.

## 2026-01-06
* 08:30 Planned the week.

## 2026-01-12

- 08:00 Next week
"""
HABITS = {"habits": {"read": ["2026-01-05", "2026-01-06", "2026-01-12"],
                     "run": ["2026-01-05", "2026-01-07", "2026-01-09", "2026-01-11"],
                     "sleep": []}}
TODOS = {"todos": [{"text": "Write report", "priority": "low", "done": False},
                   {"text": "Pay rent", "priority": "high", "done": False},
                   {"text": "Reply to Sam", "priority": "low", "done": True}]}
NOTES = {"notes": [{"text": "Buy oat milk #errands", "created": "2026-01-05 09:10"},
                   {"text": "Too early", "created": "2026-01-03 09:10"},
                   {"text": "bad date", "created": "soon"}, {"text": "no date"}]}


def test_monday_of():
    assert wr.monday_of(date(2026, 1, 7)) == MONDAY and wr.monday_of(MONDAY) == MONDAY
    assert wr.monday_of(date(2026, 1, 11)) == MONDAY


def test_journal_entries_only_this_week_and_both_bullet_styles():
    entries = wr.journal_entries(JOURNAL, MONDAY, date(2026, 1, 11))
    assert list(entries) == [date(2026, 1, 5), date(2026, 1, 6)]
    assert entries[date(2026, 1, 6)] == ["08:30 Planned the week."]
    assert wr.journal_entries("## 2026-13-45\n- x", MONDAY, MONDAY) == {}


def test_habit_rows_mark_days_and_ignore_other_weeks():
    rows = wr.habit_rows(HABITS, MONDAY)
    assert [(name, total) for name, _, total in rows] == [("run", 4), ("read", 2), ("sleep", 0)]
    assert rows[0][1] == [True, False, True, False, True, False, True]
    assert rows[1][1] == [True, True, False, False, False, False, False]


def test_notes_in_week_skips_bad_entries():
    assert wr.notes_in_week(NOTES, MONDAY, date(2026, 1, 11)) == [
        (date(2026, 1, 5), "Buy oat milk #errands")]


def test_full_review_structure():
    text = wr.build_review(MONDAY, JOURNAL, HABITS, TODOS, NOTES)
    assert text.startswith("# Weekly review: 05 Jan - 11 Jan 2026")
    assert "**Monday 05 Jan**\n- 09:10 Started with a walk." in text
    assert "| run | x | - | x | - | x | - | x | 4/7 |" in text
    assert "Finished: 1 - still open: 2" in text
    assert text.index("Pay rent (high)") < text.index("Write report (low)")  # priority order
    assert "- Mon 05 Jan: Buy oat milk #errands" in text
    assert "## Reflect" in text and text.count("**What") == len(wr.PROMPTS)
    assert text.rstrip().endswith("- [ ]")


def test_sections_are_optional_and_empty_weeks_say_so():
    bare = wr.build_review(MONDAY)
    assert "## From my journal" not in bare and "## Habits" not in bare and "## Reflect" in bare
    quiet = wr.build_review(date(2026, 3, 2), JOURNAL, None, None, NOTES)
    assert "_No journal entries this week._" in quiet and "_Nothing captured this week._" in quiet


def test_cli_with_files_and_out(tmp_path, capsys):
    paths = {}
    for name, content in [("journal.md", JOURNAL), ("habits.json", json.dumps(HABITS)),
                          ("todos.json", json.dumps(TODOS)), ("notes.json", json.dumps(NOTES))]:
        paths[name] = tmp_path / name
        paths[name].write_text(content)
    args = ["--week-of", "2026-01-07", "--journal", str(paths["journal.md"]), "--habits",
            str(paths["habits.json"]), "--todos", str(paths["todos.json"]), "--notes",
            str(paths["notes.json"])]
    assert wr.main(args) == 0
    assert "# Weekly review: 05 Jan - 11 Jan 2026" in capsys.readouterr().out
    out = tmp_path / "review.md"
    assert wr.main([*args, "--out", str(out)]) == 0
    assert out.read_text().startswith("# Weekly review")
    out.write_text("keep")
    assert wr.main([*args, "--out", str(out)]) == 1 and out.read_text() == "keep"


def test_bad_files_and_arguments(tmp_path, capsys):
    broken = tmp_path / "habits.json"
    broken.write_text("{nope")
    assert wr.main(["--habits", str(broken)]) == 1
    assert "isn't valid JSON" in capsys.readouterr().err
    broken.write_text("[1]")
    assert wr.main(["--habits", str(broken)]) == 1
    for args in (["--week-of", "someday"], ["--journal", str(tmp_path / "gone.md")]):
        with pytest.raises(SystemExit):
            wr.main(args)
