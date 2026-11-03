from grayscale_converter import main, to_grayscale
from PIL import Image


def test_colour_becomes_gray_with_equal_channels():
    gray = to_grayscale(Image.new("RGB", (4, 4), (200, 30, 30)))
    assert gray.mode == "L"
    assert 0 < gray.getpixel((0, 0)) < 255


def test_transparency_is_kept():
    img = Image.new("RGBA", (4, 4), (255, 0, 0, 0))
    img.putpixel((1, 1), (0, 255, 0, 255))
    gray = to_grayscale(img)
    assert gray.mode == "LA"
    assert gray.getpixel((0, 0))[1] == 0 and gray.getpixel((1, 1))[1] == 255


def test_contrast_stretch_spreads_values():
    img = Image.new("RGB", (2, 1))
    img.putpixel((0, 0), (100, 100, 100))
    img.putpixel((1, 0), (140, 140, 140))
    flat = to_grayscale(img)
    stretched = to_grayscale(img, contrast=True)
    assert stretched.getpixel((1, 0)) - stretched.getpixel((0, 0)) > (
        flat.getpixel((1, 0)) - flat.getpixel((0, 0)))


def test_cli_dry_run_then_apply(tmp_path):
    Image.new("RGB", (8, 8), "red").save(tmp_path / "a.jpg")
    out = tmp_path / "bw"
    main([str(tmp_path), "-o", str(out)])
    assert not out.exists()
    main([str(tmp_path), "-o", str(out), "--apply"])
    with Image.open(out / "a.jpg") as img:
        assert img.mode == "L"
