import json
import shutil
import subprocess
from datetime import date

import pytest
import repo_activity_heatmap as rah


def test_parse_dates_ignores_junk_and_time_text():
    text = "2026-06-01\n2026-06-02 10:11:12 +0000\nnonsense\n2026-13-45\n  2026-06-03\n"
    assert rah.parse_dates(text) == [date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3)]


@pytest.mark.parametrize("count,biggest,expected", [(0, 10, 0), (1, 10, 1), (3, 10, 2),
                                                    (5, 10, 2), (6, 10, 3), (10, 10, 4),
                                                    (1, 1, 4)])
def test_level(count, biggest, expected):
    assert rah.level(count, biggest) == expected


def test_week_grid_ends_in_the_week_of_end():
    columns, first = rah.week_grid({}, date(2026, 11, 25), 3)  # a Wednesday
    assert first == date(2026, 11, 9) and len(columns) == 3
    assert columns[-1][0] == date(2026, 11, 23) and columns[-1][6] == date(2026, 11, 29)


def test_streaks():
    days = {date(2026, 11, d) for d in (1, 2, 3, 10, 24, 25)}
    assert rah.streaks(days, date(2026, 11, 25)) == (3, 2)
    assert rah.streaks(days, date(2026, 11, 26)) == (3, 2)  # yesterday still counts
    assert rah.streaks(days, date(2026, 11, 28)) == (3, 0)
    assert rah.streaks(set(), date(2026, 11, 25)) == (0, 0)


def test_render_text_marks_busy_days_and_hides_future():
    counts = {date(2026, 11, 23): 4, date(2026, 11, 24): 1}
    out = rah.render_text(counts, date(2026, 11, 25), 2, rah.STYLES["ascii"])
    lines = out.splitlines()
    assert lines[1].startswith("Mon") and lines[1].endswith("#")
    assert lines[2].endswith(".") and len(lines) == 8
    assert not lines[4].rstrip().endswith(("#", ".", ":", "+"))  # Thursday is in the future


def test_render_svg_has_titles():
    svg = rah.render_svg({date(2026, 11, 25): 2}, date(2026, 11, 25), 2)
    assert svg.startswith("<svg") and "2026-11-25: 2 commit(s)" in svg
    assert "2026-11-26" not in svg and svg.endswith("</svg>")


def test_cli_text_json_svg(tmp_path, capsys):
    saved = tmp_path / "d.txt"
    saved.write_text("2026-11-23\n2026-11-23\n2026-11-24\n2026-10-01\n2025-01-01\n")
    base = ["--from-file", str(saved), "--end", "2026-11-25", "--weeks", "8"]
    assert rah.main(base) == 0
    out = capsys.readouterr().out
    assert "3 commit(s) on 2 day(s)" in out and "Busiest day: 2026-11-23 (2)" in out
    assert "Longest streak: 2 day(s); current streak: 2 day(s)" in out
    assert rah.main([*base, "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["commits"] == 3 and data["days"]["2026-11-23"] == 2
    assert data["busiest_weekday"] == "Mon"
    assert rah.main([*base, "--format", "svg", "--style", "unicode"]) == 0
    assert capsys.readouterr().out.startswith("<svg")
    assert rah.main(["--from-file", str(saved), "--end", "2020-01-01"]) == 0
    assert "0 commit(s)" in capsys.readouterr().out


def test_bad_arguments(tmp_path, capsys):
    with pytest.raises(SystemExit):
        rah.main(["--weeks", "0"])
    with pytest.raises(SystemExit):
        rah.main(["--end", "tomorrow"])
    assert rah.main(["--from-file", str(tmp_path / "missing.txt")]) == 1
    assert "Can't read the commit dates" in capsys.readouterr().err


@pytest.mark.skipif(not shutil.which("git"), reason="git is not installed")
def test_real_repository_and_author_filter(tmp_path, capsys, monkeypatch):
    def commit(name, when):
        env = {"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": f"{name}@example.com",
               "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": f"{name}@example.com",
               "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "--allow-empty", "-m", "x"],
                       check=True, capture_output=True)

    subprocess.run(["git", "-C", str(tmp_path), "init", "-q", "-b", "main"], check=True)
    commit("ann", "2026-11-23T12:00:00")
    commit("ann", "2026-11-24T12:00:00")
    commit("bob", "2026-11-24T13:00:00")
    base = ["--repo", str(tmp_path), "--end", "2026-11-25", "--weeks", "4", "--format", "json"]
    assert rah.main(base) == 0
    assert json.loads(capsys.readouterr().out)["commits"] == 3
    assert rah.main([*base, "--author", "bob"]) == 0
    assert json.loads(capsys.readouterr().out)["days"] == {"2026-11-24": 1}
    assert rah.main(["--repo", str(tmp_path / "missing")]) == 1
