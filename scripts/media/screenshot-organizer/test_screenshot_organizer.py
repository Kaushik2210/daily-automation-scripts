import os
from datetime import datetime
from pathlib import Path

from screenshot_organizer import is_screenshot, main, plan_moves, shot_date


def test_is_screenshot_by_name_and_extension():
    assert is_screenshot(Path("Screenshot 2026-03-01 at 09.30.15.png"))
    assert is_screenshot(Path("Screen Shot 2026-03-01.PNG"))
    assert is_screenshot(Path("Snip_20260301.jpg"))
    assert not is_screenshot(Path("holiday.png"))
    assert not is_screenshot(Path("screenshot notes.txt"))


def test_shot_date_from_name_or_mtime(tmp_path):
    assert shot_date(Path("Screenshot 2026-03-01 at 09.30.png")) == datetime(2026, 3, 1)
    assert shot_date(Path("Screenshot_20251231-235959.png")) == datetime(2025, 12, 31)
    f = tmp_path / "Screenshot.png"
    f.write_text("x")
    stamp = datetime(2024, 7, 9).timestamp()
    os.utime(f, (stamp, stamp))
    assert shot_date(f) == datetime(2024, 7, 9)


def test_plan_layouts(tmp_path):
    (tmp_path / "Screenshot 2026-03-01.png").write_text("x")
    (tmp_path / "photo.png").write_text("x")
    plan = plan_moves(tmp_path)
    assert [dst.relative_to(tmp_path).as_posix() for _, dst in plan] == [
        "2026/2026-03/Screenshot 2026-03-01.png"]
    month = plan_moves(tmp_path, layout="month")
    assert month[0][1].parent.name == "2026-03"


def test_dry_run_then_apply(tmp_path):
    shot = tmp_path / "Screenshot 2026-03-01.png"
    shot.write_text("x")
    main([str(tmp_path)])
    assert shot.exists()
    main([str(tmp_path), "--apply"])
    assert (tmp_path / "2026" / "2026-03" / shot.name).exists()
