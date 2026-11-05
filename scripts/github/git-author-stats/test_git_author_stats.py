import git_author_stats as gs
import pytest

US = gs.US
LOG = (
    f"@@1{US}Ada{US}ada@x{US}2026-01-13{US}feat: a\n10\t2\tf.py\n-\t-\timage.png\n\n"
    f"@@2{US}Lin{US}lin@x{US}2026-01-12{US}fix: b\n5\t5\tg.py\n\n"
    f"@@3{US}Ada{US}ada@old{US}2026-01-05{US}feat: c\n100\t0\th.py\n"
)


def test_parse_log_sums_numstat_and_skips_binary():
    commits = gs.parse_log(LOG)
    assert [(c["name"], c["added"], c["deleted"]) for c in commits] == [
        ("Ada", 10, 2), ("Lin", 5, 5), ("Ada", 100, 0)]


def test_author_stats_by_name_and_email():
    by_name = {r["author"]: r for r in gs.author_stats(gs.parse_log(LOG))}
    assert by_name["Ada"]["commits"] == 2 and by_name["Ada"]["added"] == 110
    assert by_name["Ada"]["first"] == "2026-01-05" and by_name["Ada"]["last"] == "2026-01-13"
    by_email = gs.author_stats(gs.parse_log(LOG), "email")
    assert len(by_email) == 3


def test_cli_sorting(tmp_path, capsys):
    f = tmp_path / "log.txt"
    f.write_text(LOG)
    gs.main(["--log", str(f)])
    out = capsys.readouterr().out.splitlines()
    assert out[1].startswith("Ada") and out[-1] == "3 commit(s), 2 author(s)."
    gs.main(["--log", str(f), "--sort", "lines"])
    assert capsys.readouterr().out.splitlines()[1].startswith("Ada")


def test_empty_and_missing(tmp_path, capsys):
    f = tmp_path / "empty.txt"
    f.write_text("")
    gs.main(["--log", str(f)])
    assert "No commits found." in capsys.readouterr().out
    with pytest.raises(SystemExit):
        gs.main(["--log", str(tmp_path / "nope.txt")])
