import similar_image_finder as sif
from PIL import Image, ImageDraw, ImageEnhance


def scene(size=(200, 140)):
    img = Image.new("RGB", size, (30, 90, 160))
    d = ImageDraw.Draw(img)
    d.rectangle((0, size[1] * 2 // 3, size[0], size[1]), fill=(60, 140, 70))
    d.polygon([(20, 90), (80, 20), (140, 90)], fill=(130, 110, 100))
    d.ellipse((150, 10, 190, 50), fill=(250, 210, 60))
    return img


def stripes(size=(200, 140)):
    img = Image.new("RGB", size, (200, 80, 80))
    d = ImageDraw.Draw(img)
    for x in range(0, size[0], 40):
        d.rectangle((x, 0, x + 20, size[1]), fill=(250, 240, 200))
    return img


def test_distance_counts_differing_bits():
    assert sif.distance(0b1010, 0b0110) == 2 and sif.distance(5, 5) == 0


def test_resized_and_brightened_copies_hash_close(tmp_path):
    base = scene()
    base.save(tmp_path / "a.png")
    base.resize((100, 70)).save(tmp_path / "small.png")
    ImageEnhance.Brightness(base).enhance(1.3).save(tmp_path / "bright.png")
    stripes().save(tmp_path / "other.png")
    hashes = {n: sif.dhash(tmp_path / n)[0] for n in ("a.png", "small.png", "bright.png",
                                                        "other.png")}
    assert sif.distance(hashes["a.png"], hashes["small.png"]) <= 6
    assert sif.distance(hashes["a.png"], hashes["bright.png"]) <= 6
    assert sif.distance(hashes["a.png"], hashes["other.png"]) > 10


def test_grouping_is_transitive_and_ignores_singletons():
    hashes = {"a": 0b0000, "b": 0b0001, "c": 0b0011, "z": 0b1111111111}
    assert sif.group_similar(hashes, 1) == [["a", "b", "c"]]
    assert sif.group_similar(hashes, 0) == []


def test_cli_reports_groups_and_marks_the_largest(tmp_path, capsys):
    big = scene()
    big.resize((400, 280)).save(tmp_path / "big.png")
    big.resize((100, 70)).save(tmp_path / "tiny.png")
    stripes().save(tmp_path / "other.png")
    (tmp_path / "bad.jpg").write_text("nope")
    assert sif.main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "Group 1: 2 similar images" in out and "* big.png" in out
    assert "tiny.png" in out and "skip bad.jpg" in out
    assert "Checked 3 image(s): 1 group(s), 1 possible duplicate(s)." in out


def test_recursive_and_no_duplicates(tmp_path, capsys):
    (tmp_path / "sub").mkdir()
    scene().save(tmp_path / "a.png")
    stripes().save(tmp_path / "sub" / "b.png")
    sif.main([str(tmp_path)])
    assert "Checked 1 image(s)" in capsys.readouterr().out
    sif.main([str(tmp_path), "-r"])
    assert "Checked 2 image(s): 0 group(s)" in capsys.readouterr().out
