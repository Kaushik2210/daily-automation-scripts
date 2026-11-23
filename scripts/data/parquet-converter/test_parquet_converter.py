import importlib.util
from pathlib import Path

import pandas as pd
import parquet_converter as pc
import pytest

HAVE_ENGINE = bool(importlib.util.find_spec("pyarrow") or importlib.util.find_spec("fastparquet"))
needs_engine = pytest.mark.skipif(not HAVE_ENGINE, reason="no Parquet engine installed")
CSV = "id,name,score,joined\n1,Ada,90.5,2024-01-02\n2,Bob,,2024-02-03\n3,Cy,70.25,2024-03-04\n"


def test_human():
    assert pc.human(512) == "512 B" and pc.human(2048) == "2.0 KB" and pc.human(3 << 20) == "3.0 MB"


def test_direction():
    assert pc.direction(Path("a.CSV")) == "to_parquet"
    assert pc.direction(Path("a.parquet")) == "to_csv"
    with pytest.raises(ValueError):
        pc.direction(Path("a.xlsx"))


def test_describe_counts_missing_values():
    frame = pd.DataFrame({"a": [1, 2], "b": ["x", None]})
    assert [(name, missing) for name, _, missing in pc.describe(frame)] == [("a", 0), ("b", 1)]


def test_dry_run_reports_schema_and_writes_nothing(tmp_path, capsys):
    source = tmp_path / "d.csv"
    source.write_text(CSV)
    assert pc.main([str(source)]) == 0
    out = capsys.readouterr().out
    assert "d.csv: 3 row(s) x 4 column(s)" in out and "score" in out and "1 missing" in out
    assert "Would create d.parquet" in out and not (tmp_path / "d.parquet").exists()


@needs_engine
def test_round_trip_keeps_the_data(tmp_path, capsys):
    source = tmp_path / "d.csv"
    source.write_text(CSV)
    assert pc.main([str(source), "--apply", "--compression", "gzip"]) == 0
    assert "Saved d.parquet" in capsys.readouterr().out
    back = tmp_path / "back.csv"
    assert pc.main([str(tmp_path / "d.parquet"), "-o", str(back), "--apply"]) == 0
    pd.testing.assert_frame_equal(pd.read_csv(source), pd.read_csv(back))
    assert pc.main([str(source), "--apply"]) == 1
    assert "already exists" in capsys.readouterr().err


@needs_engine
def test_every_compression_choice(tmp_path):
    source = tmp_path / "d.csv"
    source.write_text(CSV)
    for name in ("snappy", "gzip", "none"):
        target = tmp_path / f"{name}.parquet"
        assert pc.main([str(source), "-o", str(target), "--compression", name, "--apply"]) == 0
        assert len(pd.read_parquet(target)) == 3


def test_bad_inputs(tmp_path, capsys):
    with pytest.raises(SystemExit):
        pc.main([str(tmp_path / "none.csv")])
    other = tmp_path / "x.xlsx"
    other.write_text("x")
    with pytest.raises(SystemExit):
        pc.main([str(other)])
    empty = tmp_path / "e.csv"
    empty.write_text("")
    assert pc.main([str(empty)]) == 1
    assert "Can't read" in capsys.readouterr().err
    broken = tmp_path / "b.parquet"
    broken.write_text("not parquet")
    assert pc.main([str(broken)]) == 1
