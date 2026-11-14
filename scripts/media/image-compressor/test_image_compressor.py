import random

import image_compressor as ic
from PIL import Image


def noisy(path, size=(200, 150)):
    rng = random.Random(1)
    img = Image.new("RGB", size)
    img.putdata([(rng.randrange(256), rng.randrange(256), rng.randrange(256))
                 for _ in range(size[0] * size[1])])
    img.save(path, quality=98)


def test_lower_quality_makes_a_smaller_jpeg(tmp_path):
    noisy(tmp_path / "a.jpg")
    high, _, _ = ic.compress(tmp_path / "a.jpg", 90)
    low, w, h = ic.compress(tmp_path / "a.jpg", 30)
    assert len(low) < len(high) and (w, h) == (200, 150)


def test_max_side_shrinks(tmp_path):
    noisy(tmp_path / "a.jpg")
    _, w, h = ic.compress(tmp_path / "a.jpg", 80, max_side=100)
    assert (w, h) == (100, 75)


def test_human_sizes():
    assert ic.human(512) == "512 B" and ic.human(2048) == "2.0 KB"
    assert ic.human(5 * 1024 * 1024) == "5.0 MB"


def test_dry_run_apply_and_no_overwrite(tmp_path, capsys):
    noisy(tmp_path / "a.jpg")
    (tmp_path / "bad.png").write_text("nope")
    ic.main([str(tmp_path), "--quality", "30"])
    out = capsys.readouterr().out
    assert not (tmp_path / "compressed").exists() and "skip bad.png" in out
    assert "Would compress 1 image(s)" in out
    ic.main([str(tmp_path), "--quality", "30", "--apply"])
    assert (tmp_path / "compressed" / "a.jpg").stat().st_size < (tmp_path / "a.jpg").stat().st_size
    ic.main([str(tmp_path), "--quality", "30", "--apply"])
    assert "already exists" in capsys.readouterr().out


def test_already_small_files_are_kept(tmp_path, capsys):
    Image.new("RGB", (10, 10), "white").save(tmp_path / "tiny.png", optimize=True)
    ic.main([str(tmp_path), "--apply"])
    assert "keep tiny.png" in capsys.readouterr().out
    assert not (tmp_path / "compressed").exists()
