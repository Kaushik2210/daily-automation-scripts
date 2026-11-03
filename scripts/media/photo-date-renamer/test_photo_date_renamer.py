import os
from datetime import datetime

from photo_date_renamer import capture_time, main, parse_exif_date, plan_renames
from PIL import Image


def photo(path, taken=None):
    exif = Image.Exif()
    if taken:
        exif.get_ifd(0x8769)[0x9003] = taken
    Image.new("RGB", (10, 10), "red").save(path, exif=exif)


def test_parse_exif_date():
    assert parse_exif_date("2026:01:05 10:15:00") == datetime(2026, 1, 5, 10, 15)
    assert parse_exif_date("0000:00:00 00:00:00") is None
    assert parse_exif_date("garbage") is None


def test_capture_time_prefers_exif_then_file_date(tmp_path):
    photo(tmp_path / "a.jpg", "2026:01:05 10:15:00")
    assert capture_time(tmp_path / "a.jpg") == (datetime(2026, 1, 5, 10, 15), "EXIF")
    photo(tmp_path / "b.jpg")
    stamp = datetime(2020, 5, 6, 7, 8, 9).timestamp()
    os.utime(tmp_path / "b.jpg", (stamp, stamp))
    assert capture_time(tmp_path / "b.jpg") == (datetime(2020, 5, 6, 7, 8, 9), "file date")


def test_duplicate_times_get_counters(tmp_path):
    photo(tmp_path / "a.jpg", "2026:01:05 10:15:00")
    photo(tmp_path / "b.jpg", "2026:01:05 10:15:00")
    names = [n for _, n, _ in plan_renames([tmp_path / "a.jpg", tmp_path / "b.jpg"])]
    assert names == ["2026-01-05_101500.jpg", "2026-01-05_101500-2.jpg"]


def test_dry_run_then_apply(tmp_path):
    photo(tmp_path / "IMG_0001.JPG", "2026:03:01 09:00:00")
    main([str(tmp_path)])
    assert (tmp_path / "IMG_0001.JPG").exists()
    main([str(tmp_path), "--apply", "--format", "%Y%m%d"])
    assert (tmp_path / "20260301.jpg").exists()
