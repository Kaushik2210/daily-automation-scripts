import json

import page_change_detector as pcd
import pytest

OLD = "<title>T</title><h1>Jobs</h1><ul><li>Cook</li><li>Driver</li></ul><script>x=1</script>"
NEW = "<title>T</title><h1>Jobs</h1><ul><li>Cook</li><li>Pilot</li></ul><style>p{}</style>"


def test_visible_lines_skips_scripts_and_splits_blocks():
    assert pcd.visible_lines(OLD) == ["T", "Jobs", "Cook", "Driver"]
    assert pcd.visible_lines("<p>a  b\n c</p><p></p>x<br>y") == ["a b c", "x", "y"]


def test_ignore_pattern_removes_noise():
    html = "<p>Visitors: 120</p><p>News</p>"
    assert pcd.visible_lines(html, r"Visitors: \d+") == ["News"]
    assert pcd.fingerprint(pcd.visible_lines("<p>Visitors: 5</p><p>A</p>", r"Visitors: \d+")) == (
        pcd.fingerprint(pcd.visible_lines("<p>Visitors: 9</p><p>A</p>", r"Visitors: \d+")))


def test_compare_finds_added_and_removed():
    added, removed = pcd.compare(pcd.visible_lines(OLD), pcd.visible_lines(NEW))
    assert (added, removed) == (["Pilot"], ["Driver"])


def test_state_file_flow(tmp_path, capsys):
    page, state = tmp_path / "page.html", tmp_path / "state.json"
    page.write_text(OLD)
    assert pcd.main([str(page), "--state", str(state)]) == 0
    assert "First look" in capsys.readouterr().out
    assert json.loads(state.read_text())["lines"] == ["T", "Jobs", "Cook", "Driver"]
    assert pcd.main([str(page), "--state", str(state)]) == 0
    assert capsys.readouterr().out.strip() == "No change."
    page.write_text(NEW)
    assert pcd.main([str(page), "--state", str(state), "--no-update"]) == 1
    out = capsys.readouterr().out
    assert "CHANGED: 1 line(s) added, 1 removed." in out and "+ Pilot" in out
    assert "Driver" in json.loads(state.read_text())["lines"]  # baseline kept
    assert pcd.main([str(page), "--state", str(state)]) == 1  # reports again, then updates
    assert pcd.main([str(page), "--state", str(state)]) == 0


def test_previous_mode_needs_no_state(tmp_path, capsys):
    old, new = tmp_path / "old.html", tmp_path / "new.html"
    old.write_text(OLD)
    new.write_text(NEW)
    assert pcd.main([str(new), "--previous", str(old)]) == 1
    assert "- Driver" in capsys.readouterr().out
    assert pcd.main([str(old), "--previous", str(old)]) == 0


def test_errors(tmp_path, capsys):
    with pytest.raises(SystemExit):
        pcd.main([str(tmp_path / "x.html")])
    assert pcd.main([str(tmp_path / "missing.html"), "--previous", str(tmp_path / "m2")]) == 1
    page = tmp_path / "p.html"
    page.write_text(OLD)
    assert pcd.main([str(page), "--previous", str(page), "--ignore", "("]) == 1
    assert "Couldn't check" in capsys.readouterr().err
