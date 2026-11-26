import pytest
import sparkline_printer as sp

ASCII = sp.STYLES["ascii"]
BLOCKS = sp.STYLES["unicode"]


def test_parse_numbers_accepts_mixed_separators():
    assert sp.parse_numbers("1, 2;3\n4.5  -6") == [1.0, 2.0, 3.0, 4.5, -6.0]
    assert sp.parse_numbers("   ") == []
    with pytest.raises(ValueError):
        sp.parse_numbers("1 two 3")


def test_sparkline_scales_between_lowest_and_highest():
    assert sp.sparkline([1, 2, 3, 4, 5, 6, 7, 8], BLOCKS) == BLOCKS
    assert sp.sparkline([0, 10], ASCII) == "_#"
    assert sp.sparkline([5, 5, 5], ASCII) == ASCII[4] * 3  # flat line sits in the middle


def test_fixed_scale_clamps_outliers():
    assert sp.sparkline([-100, 5, 500], ASCII, low=0, high=10) == "_" + ASCII[4] + "#"


def test_resample_averages_buckets():
    assert sp.resample([1, 1, 3, 3], 2) == [1.0, 3.0]
    assert sp.resample([1, 2, 3], 10) == [1, 2, 3] and sp.resample([1, 2, 3], 0) == [1, 2, 3]
    assert len(sp.resample(list(range(100)), 7)) == 7


def test_stats_line():
    assert sp.stats([100, 150, 200]) == "min 100  max 200  last 200 (+100.0%)"
    assert sp.stats([0, 5]) == "min 0  max 5  last 5"
    assert sp.stats([2500.4, 1250.2]).endswith("(-50.0%)")


def test_read_columns_skips_blank_and_bad_cells(tmp_path):
    path = tmp_path / "d.csv"
    path.write_text("m,a,b\nx,1,\ny,\"2,000\",5\nz,oops,6\n", encoding="utf-8")
    assert sp.read_columns(path, ["a", "b"]) == {"a": [1.0, 2000.0], "b": [5.0, 6.0]}
    with pytest.raises(KeyError):
        sp.read_columns(path, ["nope"])


def test_cli_numbers_stats_and_width(capsys):
    assert sp.main(["--style", "ascii", "1", "2", "3", "4", "5", "6", "7", "8", "--stats"]) == 0
    assert capsys.readouterr().out.strip() == f"numbers  {ASCII}  min 1  max 8  last 8 (+700.0%)"
    assert sp.main(["--style", "ascii", "--width", "2", "1", "1", "9", "9"]) == 0
    assert capsys.readouterr().out.strip() == "numbers  _#"


def test_cli_file_and_csv_columns_align(tmp_path, capsys):
    numbers = tmp_path / "lat.txt"
    numbers.write_text("5 6 7\n8")
    data = tmp_path / "d.csv"
    data.write_text("a,longer_name\n1,9\n2,8\n3,7\n")
    assert sp.main(["--style", "ascii", "--from-file", str(numbers), "--csv", str(data),
                    "--column", "a", "--column", "longer_name"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [ln.split()[0] for ln in lines] == ["lat", "a", "longer_name"]
    assert len({ln.index(ln.split()[1]) for ln in lines}) == 1  # sparklines start in one column


def test_cli_errors(tmp_path, capsys):
    assert sp.main(["--from-file", str(tmp_path / "none.txt")]) == 1
    assert "Can't read the numbers" in capsys.readouterr().err
    bad = tmp_path / "bad.txt"
    bad.write_text("1 x")
    assert sp.main(["--from-file", str(bad)]) == 1
    for argv in ([], ["--csv", "a.csv"], ["--column", "a"], ["1", "--width", "-1"]):
        with pytest.raises(SystemExit):
            sp.main(argv)
