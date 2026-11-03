from gif_frame_extractor import extract, frame_info, frame_name, main
from PIL import Image


def make_gif(path, colors=("red", "green", "blue")):
    frames = [Image.new("RGB", (20, 20), c) for c in colors]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=[100, 200, 300], loop=0)


def test_frame_info_counts_and_durations(tmp_path):
    make_gif(tmp_path / "a.gif")
    assert frame_info(tmp_path / "a.gif") == [(0, 100), (1, 200), (2, 300)]


def test_frame_name_padding():
    assert frame_name("anim", 0, 5) == "anim_frame001.png"
    assert frame_name("anim", 11, 1200, "jpg") == "anim_frame0012.jpg"


def test_extract_dry_run_and_apply(tmp_path):
    make_gif(tmp_path / "a.gif")
    out = tmp_path / "frames"
    assert len(extract(tmp_path / "a.gif", out)) == 3 and not out.exists()
    extract(tmp_path / "a.gif", out, apply=True)
    assert sorted(p.name for p in out.iterdir()) == [
        "a_frame001.png", "a_frame002.png", "a_frame003.png"]
    with Image.open(out / "a_frame002.png") as img:
        assert img.convert("RGB").getpixel((0, 0))[1] > 100  # the green frame


def test_cli_single_image_and_bad_file(tmp_path, capsys):
    Image.new("RGB", (5, 5)).save(tmp_path / "still.png")
    assert main([str(tmp_path / "still.png")]) == 0
    assert "1 frame(s)" in capsys.readouterr().out
    (tmp_path / "bad.gif").write_text("nope")
    assert main([str(tmp_path / "bad.gif")]) == 1
