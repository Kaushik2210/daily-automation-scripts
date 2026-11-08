import json

import job_listing_watcher as jlw
import pytest

OLD = """<a href="/jobs/1-cook">Cook</a> <a href="/jobs/2-driver">Driver</a>
<a href="/about">About</a> <a href="mailto:jobs@x.test">Email jobs</a>"""
NEW = """<a href="/jobs/1-cook">Cook</a> <a href="/jobs/3-pilot">Chief Pilot</a>
<a href="/careers/4-data">Data Engineer</a> <a href="/jobs/3-pilot#apply">Chief Pilot</a>
<a href="/jobs/5-icon"><img src="x.png"></a>"""


def test_find_jobs_filters_links_and_resolves_them():
    jobs = jlw.find_jobs(OLD, "https://x.test/careers/")
    assert jobs == {"https://x.test/jobs/1-cook": "Cook", "https://x.test/jobs/2-driver": "Driver"}


def test_duplicates_fragments_and_imageonly_links_are_ignored():
    jobs = jlw.find_jobs(NEW, "https://x.test/")
    assert list(jobs.values()) == ["Cook", "Chief Pilot", "Data Engineer"]


def test_match_and_link_pattern():
    assert list(jlw.find_jobs(NEW, "", match="engineer|pilot").values()) == [
        "Chief Pilot", "Data Engineer"]
    assert list(jlw.find_jobs(NEW, "", link_pattern=r"/careers/").values()) == ["Data Engineer"]


def test_compare():
    old, new = jlw.find_jobs(OLD, "/"), jlw.find_jobs(NEW, "/")
    opened, closed = jlw.compare(old, new)
    assert [t for t, _ in opened] == ["Chief Pilot", "Data Engineer"]
    assert closed == [("Driver", "/jobs/2-driver")]


def test_state_flow(tmp_path, capsys):
    page, state = tmp_path / "jobs.html", tmp_path / "seen.json"
    page.write_text(OLD)
    assert jlw.main([str(page), "--state", str(state)]) == 0
    assert "First look: 2 posting(s)" in capsys.readouterr().out
    assert jlw.main([str(page), "--state", str(state)]) == 0
    assert "0 new, 0 closed, 2 unchanged." in capsys.readouterr().out
    page.write_text(NEW)
    assert jlw.main([str(page), "--state", str(state)]) == 1
    out = capsys.readouterr().out
    assert "NEW     Chief Pilot" in out and "CLOSED  Driver" in out
    assert jlw.main([str(page), "--state", str(state)]) == 0  # nothing new this time
    assert set(json.loads(state.read_text())["jobs"]) == {
        "/jobs/1-cook", "/jobs/3-pilot", "/careers/4-data"}


def test_previous_mode_and_errors(tmp_path, capsys):
    old, new = tmp_path / "old.html", tmp_path / "new.html"
    old.write_text(OLD)
    new.write_text(NEW)
    assert jlw.main([str(new), "--previous", str(old)]) == 1
    assert not list(tmp_path.glob("*.json"))
    with pytest.raises(SystemExit):
        jlw.main([str(new)])
    assert jlw.main([str(new), "--previous", str(old), "--match", "("]) == 1
    assert jlw.main([str(tmp_path / "gone.html"), "--previous", str(old)]) == 1
    assert "Couldn't check" in capsys.readouterr().err
