from datetime import date

import branch_lister as bl
import pytest

US = bl.US
REFS = (f"main{US}2026-01-13{US}Ada{US}feat: reset\n"
        f"old/experiment{US}2025-06-02{US}Max{US}try layout\n"
        f"feature/x{US}2026-01-09{US}Lin{US}feat: dark\n\n")
TODAY = date(2026, 1, 13)


def test_parse_refs_skips_blank_lines():
    branches = bl.parse_refs(REFS)
    assert [b["name"] for b in branches] == ["main", "old/experiment", "feature/x"]
    assert branches[1] == {"name": "old/experiment", "date": "2025-06-02", "author": "Max",
                           "subject": "try layout"}


def test_age_and_description():
    assert bl.age_days({"date": "2026-01-09"}, TODAY) == 4
    assert [bl.describe_age(n) for n in (0, 4, 20, 100, 800)] == [
        "today", "4d ago", "2w ago", "3mo ago", "2y ago"]


def test_cli_sorts_newest_first_and_flags_stale(tmp_path, capsys):
    f = tmp_path / "refs.txt"
    f.write_text(REFS)
    bl.main(["--refs", str(f), "--today", "2026-01-13"])
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("main") and lines[1].startswith("feature/x")
    assert lines[2].startswith("old/experiment") and lines[2].endswith("STALE")
    assert lines[-1] == "3 branch(es), 1 older than 90 days."


def test_custom_stale_limit_and_empty(tmp_path, capsys):
    f = tmp_path / "refs.txt"
    f.write_text(REFS)
    bl.main(["--refs", str(f), "--today", "2026-01-13", "--stale-days", "3"])
    assert "2 older than 3 days." in capsys.readouterr().out
    f.write_text("")
    bl.main(["--refs", str(f)])
    assert "No branches found." in capsys.readouterr().out


def test_bad_inputs(tmp_path):
    with pytest.raises(SystemExit):
        bl.main(["--refs", str(tmp_path / "none.txt")])
    f = tmp_path / "refs.txt"
    f.write_text(REFS)
    with pytest.raises(SystemExit):
        bl.main(["--refs", str(f), "--today", "yesterday"])
