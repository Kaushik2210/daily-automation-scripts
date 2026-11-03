import json

from image_metadata_reader import describe, main, read_exif
from PIL import Image


def photo(path, taken="2026:01:05 10:15:00", gps=False):
    exif = Image.Exif()
    exif[0x010F] = "TestCam"
    exif.get_ifd(0x8769)[0x9003] = taken
    if gps:
        exif.get_ifd(0x8825)[1] = "N"
    Image.new("RGB", (60, 40), "blue").save(path, exif=exif)


def test_read_exif_picks_known_fields(tmp_path):
    photo(tmp_path / "a.jpg")
    with Image.open(tmp_path / "a.jpg") as img:
        exif, gps = read_exif(img)
    assert exif["Make"] == "TestCam" and exif["DateTimeOriginal"] == "2026:01:05 10:15:00"
    assert gps is False


def test_gps_flag_detected(tmp_path):
    photo(tmp_path / "gps.jpg", gps=True)
    assert describe(tmp_path / "gps.jpg")["has_gps"] is True


def test_describe_basic_fields(tmp_path):
    Image.new("RGBA", (200, 100)).save(tmp_path / "x.png")
    info = describe(tmp_path / "x.png")
    assert info["format"] == "PNG" and info["size"] == "200x100"
    assert info["megapixels"] == 0.02 and info["exif"] == {}


def test_cli_text_and_json_and_bad_file(tmp_path, capsys):
    photo(tmp_path / "a.jpg")
    (tmp_path / "bad.png").write_text("nope")
    assert main([str(tmp_path / "a.jpg")]) == 0
    assert "Make: TestCam" in capsys.readouterr().out
    assert main([str(tmp_path / "a.jpg"), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["format"] == "JPEG"
    assert main([str(tmp_path / "bad.png")]) == 1
