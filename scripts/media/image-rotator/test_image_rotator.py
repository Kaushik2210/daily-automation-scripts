import pytest
from image_rotator import main, transform
from PIL import Image


def two_tone(size=(40, 20)):
    img = Image.new("RGB", size, "blue")
    img.paste("red", (0, 0, size[0] // 2, size[1]))  # left half red
    return img


def test_rotate_is_clockwise_and_swaps_dimensions():
    out = transform(two_tone(), rotate=90)
    assert out.size == (20, 40)
    assert out.getpixel((10, 5)) == (255, 0, 0)   # left half moved to the top
    assert out.getpixel((10, 35)) == (0, 0, 255)


def test_rotate_180_and_flip():
    assert transform(two_tone(), rotate=180).getpixel((5, 5)) == (0, 0, 255)
    assert transform(two_tone(), flip="horizontal").getpixel((5, 5)) == (0, 0, 255)
    assert transform(two_tone(), flip="vertical").getpixel((5, 5)) == (255, 0, 0)


def test_fix_orientation_uses_exif():
    img = two_tone((40, 20))
    exif = Image.Exif()
    exif[0x0112] = 6
    img.info["exif"] = exif.tobytes()
    img.getexif()[0x0112] = 6
    fixed = transform(img, fix_orientation=True)
    assert fixed.size in ((20, 40), (40, 20))


def test_cli_requires_an_action_and_applies(tmp_path):
    Image.new("RGB", (40, 20), "red").save(tmp_path / "a.png")
    with pytest.raises(SystemExit):
        main([str(tmp_path)])
    out = tmp_path / "out"
    main([str(tmp_path / "a.png"), "--rotate", "90", "-o", str(out)])
    assert not out.exists()
    main([str(tmp_path / "a.png"), "--rotate", "90", "-o", str(out), "--apply"])
    with Image.open(out / "a.png") as img:
        assert img.size == (20, 40)
