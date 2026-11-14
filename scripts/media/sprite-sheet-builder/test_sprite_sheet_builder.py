import json

import pytest
import sprite_sheet_builder as ssb
from PIL import Image


def frame(path, size, color):
    Image.new("RGBA", size, color).save(path)


def test_layout_uses_a_uniform_grid():
    cell_w, cell_h, width, height, spots = ssb.layout([(10, 8), (6, 12), (10, 10)], 2, padding=1)
    assert (cell_w, cell_h) == (10, 12)
    assert (width, height) == (1 + 2 * 11, 1 + 2 * 13)
    assert spots == [(1, 1), (12, 1), (1, 14)]


def test_build_places_each_frame_centred_in_its_cell(tmp_path):
    frame(tmp_path / "a.png", (10, 10), (255, 0, 0, 255))
    frame(tmp_path / "b.png", (4, 4), (0, 0, 255, 255))
    sheet, atlas, bad = ssb.build([tmp_path / "a.png", tmp_path / "b.png"], 2, 0)
    assert bad == [] and sheet.size == (20, 10) and atlas["cell"] == [10, 10]
    assert atlas["frames"]["b.png"] == {"x": 13, "y": 3, "w": 4, "h": 4}
    assert sheet.getpixel((13, 3)) == (0, 0, 255, 255)
    assert sheet.getpixel((10, 0))[3] == 0  # empty corner of the second cell is transparent


def test_default_columns_are_square_ish(tmp_path):
    paths = []
    for number in range(5):
        frame(tmp_path / f"{number}.png", (8, 8), "red")
        paths.append(tmp_path / f"{number}.png")
    sheet, atlas, _ = ssb.build(paths, 0, 0)
    assert sheet.size == (24, 16)  # ceil(sqrt(5)) = 3 columns, 2 rows


def test_cli_dry_run_apply_and_no_overwrite(tmp_path, capsys):
    frame(tmp_path / "a.png", (16, 16), "green")
    frame(tmp_path / "b.png", (16, 16), "blue")
    (tmp_path / "bad.png").write_text("nope")
    assert ssb.main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "2 frame(s)" in out and "skip bad.png" in out and "Dry run" in out
    assert not (tmp_path / "spritesheet.png").exists()
    assert ssb.main([str(tmp_path), "--apply", "--padding", "0"]) == 0
    atlas = json.loads((tmp_path / "spritesheet.json").read_text())
    assert atlas["image"] == "spritesheet.png" and atlas["frames"]["b.png"]["x"] == 16
    assert Image.open(tmp_path / "spritesheet.png").size == (32, 16)
    assert ssb.main([str(tmp_path), "--apply"]) == 1  # refuses, and ignores its own sheet
    assert "already exists" in capsys.readouterr().err


def test_empty_folder_and_bad_arguments(tmp_path, capsys):
    assert ssb.main([str(tmp_path)]) == 1
    assert "No images found" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        ssb.main([str(tmp_path), "--columns", "-1"])
