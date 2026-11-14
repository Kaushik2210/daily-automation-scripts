import contact_sheet_maker as csm
from PIL import Image


def make(path, color, size=(80, 40)):
    Image.new("RGB", size, color).save(path)


def test_sheet_dimensions_follow_the_grid(tmp_path):
    paths = []
    for number in range(5):
        make(tmp_path / f"{number}.png", "red")
        paths.append(tmp_path / f"{number}.png")
    sheet, bad = csm.build_sheet(paths, columns=2, thumb=64, labels=False)
    pad = max(8, 64 // 16)
    assert bad == []
    assert sheet.size == (pad + 2 * (64 + pad), pad + 3 * (64 + pad))  # 5 images -> 3 rows


def test_thumbnails_are_cropped_to_squares_in_place(tmp_path):
    make(tmp_path / "a.png", (255, 0, 0))
    sheet, _ = csm.build_sheet([tmp_path / "a.png"], 1, 32, labels=False)
    assert sheet.getpixel((2, 2)) == (255, 255, 255)  # the padding is background
    assert sheet.getpixel((8 + 16, 8 + 16)) == (255, 0, 0)  # centre of the tile


def test_unreadable_files_are_reported(tmp_path):
    make(tmp_path / "a.png", "blue")
    (tmp_path / "b.png").write_text("not an image")
    _, bad = csm.build_sheet([tmp_path / "a.png", tmp_path / "b.png"], 2, 32)
    assert bad == ["b.png"]


def test_shorten():
    assert csm.shorten("short.png", 20) == "short.png"
    assert csm.shorten("a-very-long-file-name.png", 10) == "a-very-lo…"


def test_cli_dry_run_apply_and_overwrite_refusal(tmp_path, capsys):
    make(tmp_path / "a.png", "green")
    make(tmp_path / "b.jpg", "yellow")
    assert csm.main([str(tmp_path)]) == 0
    assert "Dry run" in capsys.readouterr().out and not (tmp_path / "contact-sheet.png").exists()
    assert csm.main([str(tmp_path), "--apply", "--columns", "2"]) == 0
    assert (tmp_path / "contact-sheet.png").exists()
    # the sheet itself is never an input, and a second run refuses to overwrite it
    assert csm.main([str(tmp_path), "--apply"]) == 1
    assert "already exists" in capsys.readouterr().err


def test_empty_folder(tmp_path, capsys):
    assert csm.main([str(tmp_path)]) == 1
    assert "No images found" in capsys.readouterr().err
