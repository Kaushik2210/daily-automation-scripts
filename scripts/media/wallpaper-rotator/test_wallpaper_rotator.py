import random
from datetime import date
from pathlib import Path

import pytest
import wallpaper_rotator as wr


def make_folder(tmp_path, names=("a.png", "b.jpg", "c.jpeg", "notes.txt", "d.webp")):
    folder = tmp_path / "pics"
    folder.mkdir()
    for name in names:
        (folder / name).write_bytes(b"x")
    return folder


def test_pictures_are_sorted_and_filtered(tmp_path):
    assert [p.name for p in wr.pictures(make_folder(tmp_path))] == ["a.png", "b.jpg", "c.jpeg"]


def test_next_mode_cycles_and_handles_unknown_last():
    files = [Path("a.png"), Path("b.png"), Path("c.png")]
    assert wr.choose(files, "next", None).name == "a.png"
    assert wr.choose(files, "next", "a.png").name == "b.png"
    assert wr.choose(files, "next", "c.png").name == "a.png"
    assert wr.choose(files, "next", "gone.png").name == "a.png"


def test_random_mode_avoids_repeating_the_last_one():
    files = [Path("a.png"), Path("b.png"), Path("c.png")]
    picks = {wr.choose(files, "random", "b.png", rng=random.Random(i)).name for i in range(30)}
    assert picks == {"a.png", "c.png"}
    assert wr.choose([Path("only.png")], "random", "only.png").name == "only.png"


def test_daily_mode_is_stable_within_a_day():
    files = [Path("a.png"), Path("b.png"), Path("c.png")]
    day = date(2026, 11, 21)
    assert wr.choose(files, "daily", today=day) == wr.choose(files, "daily", "x", today=day)
    tomorrow = date(2026, 11, 22)
    assert wr.choose(files, "daily", today=day) != wr.choose(files, "daily", today=tomorrow)


def test_dry_run_does_not_change_anything(tmp_path, monkeypatch, capsys):
    folder, state = make_folder(tmp_path), tmp_path / "state.json"
    monkeypatch.setattr(wr, "command_for", lambda picture: ["setter", str(picture)])
    called = []
    monkeypatch.setattr(wr, "set_wallpaper", called.append)
    assert wr.main([str(folder), "--state", str(state)]) == 0
    out = capsys.readouterr().out
    assert "Next wallpaper: a.png" in out and "Dry run" in out
    assert called == [] and not state.exists()


def test_apply_sets_the_wallpaper_and_remembers_it(tmp_path, monkeypatch, capsys):
    folder, state = make_folder(tmp_path), tmp_path / "state.json"
    monkeypatch.setattr(wr, "command_for", lambda picture: ["setter", str(picture)])
    called = []
    monkeypatch.setattr(wr, "set_wallpaper", called.append)
    assert wr.main([str(folder), "--state", str(state), "--apply"]) == 0
    assert called[0].name == "a.png"
    assert wr.main([str(folder), "--state", str(state), "--apply"]) == 0
    assert called[1].name == "b.jpg" and "(after a.png)" not in capsys.readouterr().out.split(
        "Wallpaper changed.")[0].splitlines()[0]
    assert wr.load_state(state)[str(folder.resolve())] == "b.jpg"


def test_failures_are_reported(tmp_path, monkeypatch, capsys):
    folder = make_folder(tmp_path)
    monkeypatch.setattr(wr, "command_for", lambda picture: ["setter", str(picture)])
    monkeypatch.setattr(wr, "set_wallpaper", lambda p: (_ for _ in ()).throw(OSError("denied")))
    assert wr.main([str(folder), "--state", str(tmp_path / "s.json"), "--apply"]) == 1
    assert "Couldn't set the wallpaper: denied" in capsys.readouterr().err
    assert not (tmp_path / "s.json").exists()
    monkeypatch.setattr(wr, "command_for", lambda p: (_ for _ in ()).throw(OSError("no tool")))
    assert wr.main([str(folder), "--apply"]) == 1
    assert "Can't set the wallpaper here: no tool" in capsys.readouterr().err
    assert wr.main([str(folder)]) == 0  # a dry run still shows the choice
    assert "This system can't set the wallpaper" in capsys.readouterr().out
    empty = tmp_path / "empty"
    empty.mkdir()
    assert wr.main([str(empty)]) == 1
    with pytest.raises(SystemExit):
        wr.main([str(tmp_path / "missing")])


def test_corrupt_state_file_is_ignored(tmp_path):
    state = tmp_path / "s.json"
    state.write_text("{broken")
    assert wr.load_state(state) == {} and wr.load_state(tmp_path / "none.json") == {}
