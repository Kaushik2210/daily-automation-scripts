import exif_stripper as es
from PIL import Image


def photo(path, gps=True):
    img = Image.new("RGB", (40, 30), (10, 120, 200))
    exif = Image.Exif()
    exif[0x010F] = "Canon"
    exif[0x0110] = "EOS 90D"
    exif[0x0132] = "2026:03:01 09:30:15"
    if gps:
        exif[0x8825] = {1: "N", 2: (12.0, 58.0, 0.0), 3: "E", 4: (77.0, 35.0, 0.0)}
    img.save(path, exif=exif)


def test_describe_lists_sensitive_data(tmp_path):
    photo(tmp_path / "a.jpg")
    with Image.open(tmp_path / "a.jpg") as img:
        found = es.describe(img)
    assert "GPS location" in found and "camera Canon EOS 90D" in found
    assert "date 2026:03:01 09:30:15" in found


def test_clean_copy_has_no_exif_but_same_pixels(tmp_path):
    photo(tmp_path / "a.jpg")
    with Image.open(tmp_path / "a.jpg") as img:
        clean = es.clean_copy(img)
        assert len(clean.getexif()) == 0 and clean.size == (40, 30)
        assert clean.getpixel((5, 5)) == img.convert("RGB").getpixel((5, 5))


def test_dry_run_then_apply_leaves_original_alone(tmp_path, capsys):
    photo(tmp_path / "a.jpg")
    photo(tmp_path / "b.jpg", gps=False)
    Image.new("RGB", (8, 8), "red").save(tmp_path / "plain.png")
    es.main([str(tmp_path)])
    out = capsys.readouterr().out
    assert not (tmp_path / "clean").exists()
    assert "a.jpg: removes GPS location" in out and "plain.png: no metadata found" in out
    assert "Would clean 3 photo(s); 2 carried metadata." in out
    es.main([str(tmp_path), "--apply"])
    with Image.open(tmp_path / "clean" / "a.jpg") as cleaned:
        assert not cleaned.getexif().get_ifd(es.GPS_IFD) and len(cleaned.getexif()) == 0
    with Image.open(tmp_path / "a.jpg") as original:
        assert original.getexif().get_ifd(es.GPS_IFD)


def test_existing_output_and_bad_files_are_skipped(tmp_path, capsys):
    photo(tmp_path / "a.jpg")
    (tmp_path / "bad.png").write_text("nope")
    es.main([str(tmp_path), "--apply"])
    es.main([str(tmp_path), "--apply"])
    out = capsys.readouterr().out
    assert "skip bad.png" in out and "a.jpg already exists" in out
