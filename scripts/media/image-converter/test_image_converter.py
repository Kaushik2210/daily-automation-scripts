from image_converter import convert, main, prepare
from PIL import Image


def make(path, mode="RGB", size=(40, 20), color="red"):
    Image.new(mode, size, color).save(path)


def test_prepare_flattens_transparency_for_jpeg():
    rgba = Image.new("RGBA", (4, 4), (255, 0, 0, 0))
    flat = prepare(rgba, "JPEG")
    assert flat.mode == "RGB" and flat.getpixel((0, 0)) == (255, 255, 255)
    assert prepare(Image.new("L", (2, 2)), "JPEG").mode == "RGB"
    assert prepare(rgba, "PNG").mode == "RGBA"


def test_convert_png_to_jpg_and_webp(tmp_path):
    make(tmp_path / "a.png", "RGBA", color=(0, 0, 255, 128))
    out = convert(tmp_path / "a.png", "JPEG", tmp_path)
    assert out.name == "a.jpg"
    with Image.open(out) as img:
        assert img.format == "JPEG"
    webp = convert(tmp_path / "a.png", "WEBP", tmp_path)
    with Image.open(webp) as img:
        assert img.format == "WEBP"


def test_dry_run_and_skip_same_format(tmp_path, capsys):
    make(tmp_path / "a.png")
    make(tmp_path / "b.jpg")
    out = tmp_path / "out"
    main([str(tmp_path), "--to", "png", "-o", str(out)])
    text = capsys.readouterr().out
    assert "skip a.png: already png" in text and "b.jpg -> b.png" in text
    assert not out.exists()


def test_apply_writes_files(tmp_path):
    make(tmp_path / "a.png")
    out = tmp_path / "out"
    main([str(tmp_path / "a.png"), "--to", "bmp", "-o", str(out), "--apply"])
    with Image.open(out / "a.bmp") as img:
        assert img.format == "BMP"
