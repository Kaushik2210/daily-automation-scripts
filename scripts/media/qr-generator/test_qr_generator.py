import qr_generator as qg


def test_matrix_is_square_with_border_and_grows_with_data():
    short = qg.build("hi").get_matrix()
    longer = qg.build("x" * 200).get_matrix()
    assert len(short) == len(short[0]) and len(longer) > len(short)
    assert not any(short[0])  # quiet-zone border is empty


def test_finder_patterns_in_corners():
    matrix = qg.build("hello", border=0).get_matrix()
    assert matrix[0][:7] == [True] * 7            # top-left finder, top row
    assert matrix[0][-7:] == [True] * 7           # top-right finder
    assert all(matrix[6][:7])                      # bottom of the top-left finder


def test_text_rendering_modes():
    matrix = [[True, False], [False, True]]
    assert qg.to_text(matrix, ascii_only=True) == "##  \n  ##"
    assert qg.to_text(matrix) == "▀▄"


def test_error_level_changes_capacity():
    assert qg.build("x" * 120, "H").version >= qg.build("x" * 120, "L").version


def test_cli_preview_then_apply(tmp_path, capsys):
    svg = tmp_path / "code.svg"
    qg.main(["https://example.com", "--ascii", "-o", str(svg)])
    assert not svg.exists() and "preview only" in capsys.readouterr().out
    qg.main(["https://example.com", "--ascii", "-o", str(svg), "--apply"])
    assert svg.read_text(encoding="utf-8").lstrip().startswith(("<?xml", "<svg"))
