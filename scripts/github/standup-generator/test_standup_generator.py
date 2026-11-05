from datetime import date

import pytest
import standup_generator as sg

US = sg.US
LOG = (
    f"@@aaaaaaa1{US}Ada{US}ada@x.com{US}2026-01-13{US}feat: add reset flow\n"
    f"@@bbbbbbb2{US}Lin{US}lin@x.com{US}2026-01-12{US}fix(cart): handle empty cart.\n"
    f"@@ccccccc3{US}Ada{US}ada@x.com{US}2026-01-12{US}docs: update guide\n"
    f"@@ddddddd4{US}Ada{US}ada@x.com{US}2026-01-09{US}chore: older\n"
)


def test_parse_log_fields():
    commits = sg.parse_log(LOG)
    assert len(commits) == 4
    assert commits[0] == {"sha": "aaaaaaa1", "name": "Ada", "email": "ada@x.com",
                          "date": "2026-01-13", "subject": "feat: add reset flow"}


def test_previous_workday_skips_weekends():
    assert sg.previous_workday(date(2026, 1, 13)) == date(2026, 1, 12)   # Tue -> Mon
    assert sg.previous_workday(date(2026, 1, 12)) == date(2026, 1, 9)    # Mon -> Fri
    assert sg.previous_workday(date(2026, 1, 11)) == date(2026, 1, 9)    # Sun -> Fri


def test_friendly_strips_prefix_and_period():
    assert sg.friendly("feat(ui)!: add dark mode.") == "Add dark mode"
    assert sg.friendly("plain message") == "Plain message"


def test_standup_filters_author_and_groups_days():
    text = sg.build_standup(sg.parse_log(LOG), date(2026, 1, 13), author="ada")
    assert "Yesterday (Mon 2026-01-12):\n- Update guide (ccccccc)" in text
    assert "Today so far:\n- Add reset flow (aaaaaaa)" in text
    assert "Lin" not in text and "cart" not in text
    raw = sg.build_standup(sg.parse_log(LOG), date(2026, 1, 13), "ada", raw=True)
    assert "- docs: update guide (ccccccc)" in raw


def test_no_commits_and_cli(tmp_path, capsys):
    log = tmp_path / "log.txt"
    log.write_text(LOG)
    sg.main(["--log", str(log), "--today", "2026-01-14", "--author", "lin"])
    out = capsys.readouterr().out
    assert "(no commits)" in out and "Blockers:\n- None" in out
    with pytest.raises(SystemExit):
        sg.main(["--log", str(log), "--today", "tomorrow"])
