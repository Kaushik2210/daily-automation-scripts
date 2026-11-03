from PIL import Image
from thumbnail_generator import main, make_thumbnail, thumbnail_name


def make(path, size=(400, 200)):
    Image.new("RGB", size, "green").save(path)


def test_thumbnail_name():
    assert thumbnail_name(__import__("pathlib").Path("a/photo.JPG")) == "photo_thumb.JPG"


def test_fit_keeps_aspect_and_never_enlarges(tmp_path):
    make(tmp_path / "wide.png", (400, 200))
    assert make_thumbnail(tmp_path / "wide.png", 100).size == (100, 50)
    make(tmp_path / "tiny.png", (20, 10))
    assert make_thumbnail(tmp_path / "tiny.png", 100).size == (20, 10)


def test_square_crop(tmp_path):
    make(tmp_path / "wide.png", (400, 200))
    assert make_thumbnail(tmp_path / "wide.png", 64, square=True).size == (64, 64)


def test_dry_run_then_apply_skips_bad_files(tmp_path, capsys):
    make(tmp_path / "a.png")
    (tmp_path / "bad.jpg").write_text("not an image")
    main([str(tmp_path), "--size", "50"])
    assert not (tmp_path / "thumbs").exists()
    assert "skip bad.jpg" in capsys.readouterr().out
    main([str(tmp_path), "--size", "50", "--apply"])
    with Image.open(tmp_path / "thumbs" / "a_thumb.png") as img:
        assert img.size == (50, 25)
