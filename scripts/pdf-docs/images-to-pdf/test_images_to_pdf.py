import images_to_pdf as ip
from PIL import Image
from pypdf import PdfReader


def make(path, size=(300, 200), mode="RGB", color="red"):
    Image.new(mode, size, color).save(path)


def test_flatten_transparency_to_white():
    rgba = Image.new("RGBA", (4, 4), (255, 0, 0, 0))
    flat = ip.flatten(rgba)
    assert flat.mode == "RGB" and flat.getpixel((0, 0)) == (255, 255, 255)


def test_to_a4_orientation_and_centering():
    portrait = ip.to_a4(Image.new("RGB", (100, 200), "black"))
    landscape = ip.to_a4(Image.new("RGB", (200, 100), "black"))
    assert portrait.size == ip.A4_PIXELS and landscape.size == ip.A4_PIXELS[::-1]
    assert portrait.getpixel((0, 0)) == (255, 255, 255)                 # white margin
    centre = (portrait.width // 2, portrait.height // 2)
    assert portrait.getpixel(centre) == (0, 0, 0)                       # image in the middle


def test_collect_sorts_folders_and_keeps_given_order(tmp_path):
    make(tmp_path / "b.png")
    make(tmp_path / "a.jpg")
    (tmp_path / "notes.txt").write_text("x")
    assert [p.name for p in ip.collect([tmp_path])] == ["a.jpg", "b.png"]
    given = [tmp_path / "b.png", tmp_path / "a.jpg"]
    assert ip.collect(given) == given


def test_cli_dry_run_apply_and_skip_bad(tmp_path, capsys):
    make(tmp_path / "a.png", (300, 200))
    make(tmp_path / "b.png", (200, 300))
    (tmp_path / "bad.png").write_text("nope")
    out = tmp_path / "out.pdf"
    args = [str(tmp_path / "a.png"), str(tmp_path / "b.png"), str(tmp_path / "bad.png"),
            "-o", str(out)]
    assert ip.main(args) == 0 and not out.exists()
    assert "skip bad.png" in capsys.readouterr().out
    assert ip.main([*args, "--apply"]) == 0
    reader = PdfReader(str(out))
    assert len(reader.pages) == 2
    assert ip.main([*args, "--apply"]) == 1


def test_fit_size_matches_each_image(tmp_path):
    make(tmp_path / "a.png", (300, 200))
    out = tmp_path / "fit.pdf"
    ip.main([str(tmp_path / "a.png"), "--size", "fit", "-o", str(out), "--apply"])
    box = PdfReader(str(out)).pages[0].mediabox
    assert round(float(box.width) / float(box.height), 2) == 1.5
