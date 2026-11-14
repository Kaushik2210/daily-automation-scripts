import json

import palette_extractor as pe
import pytest
from PIL import Image, ImageDraw

NAVY, ORANGE, SAND = (20, 60, 130), (235, 90, 60), (245, 215, 120)


def demo(path):
    img = Image.new("RGB", (200, 100), NAVY)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 50, 99, 99), fill=ORANGE)
    d.rectangle((100, 50, 199, 99), fill=SAND)
    img.save(path)
    return path


def close(a, b, tolerance=12):
    return all(abs(x - y) <= tolerance for x, y in zip(a, b, strict=True))


def test_extracts_colors_in_order_of_share(tmp_path):
    colors = pe.extract(demo(tmp_path / "d.png"), 3)
    assert [round(share, 2) for _, share in colors] == [0.5, 0.25, 0.25]
    assert close(colors[0][0], NAVY)
    assert any(close(c, ORANGE) for c, _ in colors)
    assert any(close(c, SAND) for c, _ in colors)


def test_transparent_pixels_count_as_white(tmp_path):
    Image.new("RGBA", (20, 20), (0, 0, 0, 0)).save(tmp_path / "t.png")
    (rgb, share), = pe.extract(tmp_path / "t.png", 3)
    assert rgb == (255, 255, 255) and share == 1.0


def test_hex_and_names():
    assert pe.hex_code((255, 0, 128)) == "#FF0080"
    assert pe.color_name((10, 30, 100)) == "navy" and pe.color_name((250, 250, 250)) == "white"
    assert pe.color_name((50, 150, 60)) == "green"


def test_cli_table_json_and_swatch(tmp_path, capsys):
    path = demo(tmp_path / "d.png")
    assert pe.main([str(path), "-n", "3"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 3 and "navy" in out[0] and "50.0%" in out[0]
    assert pe.main([str(path), "-n", "3", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["name"] == "navy" and data[0]["share"] == 0.5
    swatch = tmp_path / "strip.png"
    assert pe.main([str(path), "-n", "3", "--swatch", str(swatch)]) == 0
    assert Image.open(swatch).size == (600, 120)
    with pytest.raises(SystemExit):
        pe.main([str(path), "--swatch", str(swatch)])  # never overwrites


def test_bad_inputs(tmp_path, capsys):
    (tmp_path / "x.png").write_text("nope")
    assert pe.main([str(tmp_path / "x.png")]) == 1
    assert "Can't read" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        pe.main([str(tmp_path / "x.png"), "-n", "99"])
