import shutil
import subprocess
from pathlib import Path

import pytest
import video_frame_grabber as vfg


def test_frame_times():
    assert vfg.frame_times(35, 10) == [0, 10, 20, 30]
    assert vfg.frame_times(30, 10) == [0, 10, 20]  # 30 s is the end, not a frame
    assert vfg.frame_times(100, 10, start=5, count=3) == [5, 15, 25]
    assert vfg.frame_times(5, 2.5) == [0, 2.5]
    assert vfg.frame_times(3, 10, start=5) == []


def test_names_and_command(tmp_path):
    assert vfg.frame_name("clip", 12.5, "jpg") == "clip_00012500ms.jpg"
    command = vfg.grab_command(Path("v.mp4"), 3.2, Path("out.jpg"))
    assert command[:5] == ["ffmpeg", "-v", "error", "-n", "-ss"] and "3.200" in command
    assert command[-1] == "out.jpg" and "-frames:v" in command


def test_clock():
    assert vfg.clock(3725.9) == "1:02:05" and vfg.clock(59) == "0:00:59"


def test_dry_run_plans_without_ffmpeg(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert vfg.main(["holiday.mp4", "--duration", "45", "--every", "20"]) == 0
    out = capsys.readouterr().out
    assert "0:00:45 long, one frame every 20s" in out
    assert "0:00:20 -> holiday_00020000ms.jpg" in out
    assert "Would save 3 frame(s)" in out and not (tmp_path / "frames").exists()


def test_apply_runs_ffmpeg_for_each_frame_and_skips_existing(tmp_path, monkeypatch, capsys):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        Path(command[-1]).write_bytes(b"jpeg")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(subprocess, "run", fake_run)
    out_dir = tmp_path / "shots"
    args = ["v.mp4", "--duration", "25", "--every", "10", "-o", str(out_dir), "--apply"]
    assert vfg.main(args) == 0
    assert len(calls) == 3 and "Saved 3 frame(s)" in capsys.readouterr().out
    assert vfg.main(args) == 0
    assert len(calls) == 3  # nothing was grabbed twice
    assert "already exists" in capsys.readouterr().out


def test_failures_and_missing_tools(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert vfg.main(["v.mp4", "--duration", "20", "-o", str(tmp_path), "--apply"]) == 1
    assert "install FFmpeg" in capsys.readouterr().err
    monkeypatch.chdir(tmp_path)
    assert vfg.main(["--duration", "3", "v.mp4", "--start", "9"]) == 1
    assert "Nothing to grab" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        vfg.main(["ghost.mp4"])
    plan = [str(tmp_path / "x.mp4"), "--duration", "5", "--every", "1", "--count", "2"]
    assert vfg.main(plan) == 0


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg is not installed")
def test_real_video(tmp_path):
    clip = tmp_path / "t.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=10",
                    "-t", "3", "-pix_fmt", "yuv420p", str(clip)], check=True)
    assert 2.9 < vfg.video_duration(clip) < 3.2
    out_dir = tmp_path / "frames"
    assert vfg.main([str(clip), "--every", "1", "-o", str(out_dir), "--apply"]) == 0
    assert len(list(out_dir.glob("*.jpg"))) == 3
