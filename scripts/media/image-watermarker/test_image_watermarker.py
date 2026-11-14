import image_watermarker as iw
import pytest
from PIL import Image


def blank(path, size=(300, 200), color="black"):
    Image.new("RGB", size, color).save(path)


def test_watermark_changes_pixels_only_near_the_chosen_corner(tmp_path):
    blank(tmp_path / "a.png")
    marked = iw.watermark(tmp_path / "a.png", "TEST", "bottom-right", 100, 10).convert("RGB")
    assert marked.size == (300, 200)
    extrema = marked.crop((150, 100, 300, 200)).getextrema()
    assert max(high for _, high in extrema) > 200  # white text appeared at the bottom right
    assert marked.crop((0, 0, 150, 100)).getbbox() is None  # top-left stays black


def test_zero_opacity_leaves_the_image_unchanged(tmp_path):
    blank(tmp_path / "a.png", color="navy")
    marked = iw.watermark(tmp_path / "a.png", "TEST", opacity=0).convert("RGB")
    assert marked.tobytes() == Image.open(tmp_path / "a.png").convert("RGB").tobytes()


@pytest.mark.parametrize("position,expected", [
    ("top-left", (5, 5)), ("bottom-right", (85, 35)), ("center", (45, 20))])
def test_positions(position, expected):
    assert iw.place(position, (100, 50), (10, 10), 5) == expected


def test_cli_dry_run_apply_and_skip(tmp_path, capsys):
    blank(tmp_path / "a.jpg")
    (tmp_path / "bad.png").write_text("nope")
    iw.main([str(tmp_path), "--text", "hi"])
    out = capsys.readouterr().out
    assert "Would watermark 1 image(s)" in out and "skip bad.png" in out
    assert not (tmp_path / "watermarked").exists()
    iw.main([str(tmp_path), "--text", "hi", "--apply"])
    assert Image.open(tmp_path / "watermarked" / "a.jpg").size == (300, 200)
    iw.main([str(tmp_path), "--text", "hi", "--apply"])
    assert "already exists" in capsys.readouterr().out


def test_bad_arguments(tmp_path):
    with pytest.raises(SystemExit):
        iw.main([str(tmp_path), "--text", "x", "--opacity", "150"])
    with pytest.raises(SystemExit):
        iw.main([str(tmp_path / "missing"), "--text", "x"])
