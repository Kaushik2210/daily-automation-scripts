import pytest
from image_resizer import collect_images, main, target_size
from PIL import Image


def make_image(path, size=(400, 200), color="red"):
    Image.new("RGB", size, color).save(path)


def test_target_size_variants():
    assert target_size((400, 200), width=100) == (100, 50)
    assert target_size((400, 200), height=50) == (100, 50)
    assert target_size((400, 200), percent=50) == (200, 100)
    assert target_size((400, 200), width=100, height=100) == (100, 50)
    assert target_size((10, 10), percent=1) == (1, 1)
    with pytest.raises(ValueError):
        target_size((10, 10))


def test_collect_images_filters_by_extension(tmp_path):
    make_image(tmp_path / "a.png")
    make_image(tmp_path / "b.JPG")
    (tmp_path / "notes.txt").write_text("x")
    assert [p.name for p in collect_images([tmp_path])] == ["a.png", "b.JPG"]


def test_dry_run_writes_nothing(tmp_path, capsys):
    make_image(tmp_path / "a.png")
    out = tmp_path / "out"
    main([str(tmp_path / "a.png"), "--width", "100", "-o", str(out)])
    assert not out.exists()
    assert "400x200 -> 100x50" in capsys.readouterr().out


def test_apply_resizes_and_skips_bad_files(tmp_path):
    make_image(tmp_path / "a.png")
    (tmp_path / "fake.png").write_text("not an image")
    out = tmp_path / "out"
    main([str(tmp_path), "--percent", "25", "-o", str(out), "--apply"])
    with Image.open(out / "a.png") as img:
        assert img.size == (100, 50)
    assert not (out / "fake.png").exists()
