import json
import shutil
import subprocess

import pytest
import video_info_reporter as vir

PROBE = {
    "streams": [
        {"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720,
         "avg_frame_rate": "30000/1001", "pix_fmt": "yuv420p"},
        {"codec_type": "audio", "codec_name": "aac", "sample_rate": "44100", "channels": 2,
         "channel_layout": "stereo"}],
    "format": {"filename": "clip.mp4", "duration": "65.5", "size": "5242880",
               "bit_rate": "640000", "tags": {"title": "Demo"}}}


def test_summarise_rows():
    rows = dict(vir.summarise(PROBE))
    assert rows["Duration"] == "1:06" and rows["Size"] == "5.0 MB"
    assert rows["Bitrate"] == "640 kbps overall"
    assert rows["Video"] == "h264, 1280x720, 29.97 fps, yuv420p"
    assert rows["Audio"] == "aac, 44.1 kHz, stereo" and rows["Title"] == "Demo"


def test_fps_and_clock_helpers():
    assert vir.fps("25/1") == "25" and vir.fps("30000/1001") == "29.97"
    assert vir.fps("0/0") is None and vir.fps("junk") is None
    assert vir.clock(3725) == "1:02:05" and vir.clock(59.6) == "1:00"


def test_from_json_cli(tmp_path, capsys):
    saved = tmp_path / "probe.json"
    saved.write_text(json.dumps(PROBE))
    assert vir.main(["--from-json", str(saved)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("clip.mp4\n") and "Video      h264, 1280x720" in out
    assert "1 video(s), 1:06 in total." in out


def test_bad_json_and_missing_inputs(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{nope")
    assert vir.main(["--from-json", str(bad)]) == 1
    assert "can't read it" in capsys.readouterr().out
    assert vir.main([str(tmp_path / "ghost.mp4")]) == 1
    with pytest.raises(SystemExit):
        vir.main([])


def test_missing_ffprobe_is_a_clear_message(tmp_path, monkeypatch, capsys):
    clip = tmp_path / "a.mp4"
    clip.write_bytes(b"x")
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert vir.main([str(clip)]) == 1
    assert "install FFmpeg" in capsys.readouterr().out


def test_probe_uses_ffprobe_output(tmp_path, monkeypatch):
    clip = tmp_path / "a.mp4"
    clip.write_bytes(b"x")
    monkeypatch.setattr(shutil, "which", lambda name: "/bin/ffprobe")
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, json.dumps(PROBE), "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert vir.probe(clip)["format"]["duration"] == "65.5"
    assert seen["cmd"][0] == "/bin/ffprobe" and str(clip) == seen["cmd"][-1]


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg is not installed")
def test_real_video(tmp_path):
    clip = tmp_path / "t.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=10",
                    "-t", "2", "-pix_fmt", "yuv420p", str(clip)], check=True)
    rows = dict(vir.summarise(vir.probe(clip)))
    assert rows["Video"].startswith("h264, 160x120, 10 fps")
    assert rows["Duration"] == "0:02"
