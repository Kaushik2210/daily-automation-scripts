import pytest
import srt_shifter as ss

SRT = """1
00:00:01,000 --> 00:00:03,500
Hello there.

2
00:00:04,000 --> 00:00:06,000
Second line
over two rows.

3
00:01:00,000 --> 00:01:02,000
Later on.
"""


@pytest.mark.parametrize("text,ms", [
    ("2.5", 2500), ("+2.5", 2500), ("-1.2s", -1200), ("1500ms", 1500), ("-1m30s", -90000),
    ("2m", 120000), ("-00:00:01,500", -1500), ("00:01:05", 65000), ("1:02:03.250", 3723250)])
def test_parse_offset(text, ms):
    assert ss.parse_offset(text) == ms


@pytest.mark.parametrize("bad", ["", "soon", "1x", "--"])
def test_parse_offset_rejects_nonsense(bad):
    with pytest.raises(ValueError):
        ss.parse_offset(bad)


def test_fmt_and_roundtrip():
    assert ss.fmt(3723250) == "01:02:03,250" and ss.fmt(-5) == "00:00:00,000"
    cues = ss.parse_srt(SRT)
    assert cues[1] == (4000, 6000, ["Second line", "over two rows."])
    assert ss.parse_srt(ss.render(cues)) == cues


def test_shift_forward_and_after():
    cues = ss.parse_srt(SRT)
    shifted, dropped = ss.shift(cues, 2000)
    assert [c[0] for c in shifted] == [3000, 6000, 62000] and dropped == 0
    partial, _ = ss.shift(cues, 2000, after=60000)
    assert [c[0] for c in partial] == [1000, 4000, 62000]


def test_negative_shift_clamps_and_drops():
    cues = ss.parse_srt(SRT)
    shifted, dropped = ss.shift(cues, -2000)
    assert shifted[0][:2] == (0, 1500) and dropped == 0
    shifted, dropped = ss.shift(cues, -3500)
    assert dropped == 1 and shifted[0][0] == 500


def test_cli_dry_run_apply_and_refusal(tmp_path, capsys):
    source = tmp_path / "movie.srt"
    source.write_text(SRT)
    assert ss.main([str(source), "--shift", "2.5"]) == 0
    out = capsys.readouterr().out
    assert "00:00:01,000 -> 00:00:03,500  Hello there." in out and "Dry run" in out
    assert not (tmp_path / "movie.shifted.srt").exists()
    assert ss.main([str(source), "--shift=-0.5", "--apply"]) == 0
    result = (tmp_path / "movie.shifted.srt").read_text()
    assert "00:00:00,500 --> 00:00:03,000" in result and result.startswith("1\n")
    assert ss.main([str(source), "--shift", "1", "--apply"]) == 1
    assert "already exists" in capsys.readouterr().err


def test_cli_errors(tmp_path, capsys):
    source = tmp_path / "a.srt"
    source.write_text("nothing here")
    assert ss.main([str(source), "--shift", "1"]) == 1
    assert "No subtitle cues" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        ss.main([str(source), "--shift", "banana"])
    with pytest.raises(SystemExit):
        ss.main([str(tmp_path / "gone.srt"), "--shift", "1"])
