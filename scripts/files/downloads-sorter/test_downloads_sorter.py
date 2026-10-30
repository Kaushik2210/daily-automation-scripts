import os
from datetime import datetime

from downloads_sorter import main, month_folder, plan_moves


def make_file(path, year, month):
    path.write_text("x")
    stamp = datetime(year, month, 15, 12).timestamp()
    os.utime(path, (stamp, stamp))


def test_month_folder(tmp_path):
    f = tmp_path / "a.txt"
    make_file(f, 2025, 3)
    assert month_folder(f) == "2025-03"


def test_plan_skips_hidden_and_dirs(tmp_path):
    make_file(tmp_path / "a.txt", 2025, 3)
    make_file(tmp_path / ".hidden", 2025, 3)
    (tmp_path / "2025-01").mkdir()
    plan = plan_moves(tmp_path)
    assert [src.name for src, _ in plan] == ["a.txt"]


def test_dry_run_then_apply(tmp_path):
    make_file(tmp_path / "a.txt", 2024, 12)
    main([str(tmp_path)])
    assert (tmp_path / "a.txt").exists()
    main([str(tmp_path), "--apply"])
    assert (tmp_path / "2024-12" / "a.txt").exists()
