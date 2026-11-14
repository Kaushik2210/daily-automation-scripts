import math
import struct
import wave

import audio_metadata_reader as amr


def id3_frame(frame_id, text):
    body = b"\x00" + text.encode("latin-1")
    return frame_id.encode() + struct.pack(">I", len(body)) + b"\x00\x00" + body


def syncsafe(n):
    return bytes([(n >> 21) & 0x7F, (n >> 14) & 0x7F, (n >> 7) & 0x7F, n & 0x7F])


def make_mp3(path, frames=100, with_v1=False):
    body = b"".join(id3_frame(i, t) for i, t in
                    [("TIT2", "Song"), ("TPE1", "Band"), ("TRCK", "2/10"), ("TYER", "2024")])
    data = b"ID3\x03\x00\x00" + syncsafe(len(body)) + body
    data += (b"\xff\xfb\x90\x00" + b"\x00" * 413) * frames  # 128 kbps, 44.1 kHz, 417 bytes each
    if with_v1:
        data += b"TAG" + b"Old Title".ljust(30, b"\x00") + b"Old Artist".ljust(30, b"\x00")
        data += b"Old Album".ljust(30, b"\x00") + b"1999" + b"".ljust(30, b"\x00") + b"\x08"
    path.write_bytes(data)
    return path


def make_flac(path, seconds=200):
    vendor = b"x"
    comments = [b"TITLE=Night", b"TRACKNUMBER=4", b"DATE=2020"]
    vorbis = struct.pack("<I", len(vendor)) + vendor + struct.pack("<I", len(comments))
    vorbis += b"".join(struct.pack("<I", len(c)) + c for c in comments)
    packed = (44100 << 44) | (1 << 41) | (15 << 36) | (44100 * seconds)
    info = struct.pack(">HH", 4096, 4096) + b"\x00" * 6 + packed.to_bytes(8, "big") + b"\x00" * 16
    path.write_bytes(b"fLaC" + b"\x00" + len(info).to_bytes(3, "big") + info
                     + b"\x84" + len(vorbis).to_bytes(3, "big") + vorbis)
    return path


def make_wav(path, seconds=1.0, rate=8000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(5000 * math.sin(n / 5)))
                               for n in range(int(rate * seconds))))
    return path


def test_mp3_tags_and_duration(tmp_path):
    info = amr.read_audio(make_mp3(tmp_path / "a.mp3", frames=100))
    assert info["tags"] == {"title": "Song", "artist": "Band", "track": "2/10", "year": "2024"}
    assert (info["bitrate"], info["sample_rate"], info["channels"]) == (128, 44100, 2)
    assert round(info["duration"], 2) == round(100 * 417 * 8 / 128000, 2)


def test_id3v1_fills_gaps_but_does_not_override(tmp_path):
    info = amr.read_audio(make_mp3(tmp_path / "a.mp3", with_v1=True))
    assert info["tags"]["title"] == "Song" and info["tags"]["album"] == "Old Album"
    assert info["tags"]["genre"] == "Jazz"


def test_flac_streaminfo_and_comments(tmp_path):
    info = amr.read_audio(make_flac(tmp_path / "a.flac"))
    assert info["duration"] == 200 and info["sample_rate"] == 44100
    assert (info["channels"], info["bits"]) == (2, 16)
    assert info["tags"] == {"title": "Night", "track": "4", "year": "2020"}


def test_wav_duration(tmp_path):
    info = amr.read_audio(make_wav(tmp_path / "a.wav", seconds=1.5))
    assert info["duration"] == 1.5 and info["channels"] == 1 and info["bits"] == 16


def test_clock_and_describe():
    assert amr.clock(75) == "1:15" and amr.clock(3725) == "1:02:05"
    text = amr.describe({"duration": 200, "bitrate": 320, "sample_rate": 44100, "channels": 2})
    assert text == "3:20, 320 kbps, 44.1 kHz, stereo"


def test_cli_folder_with_bad_and_unrelated_files(tmp_path, capsys):
    make_mp3(tmp_path / "a.mp3")
    make_wav(tmp_path / "b.wav")
    (tmp_path / "broken.flac").write_bytes(b"nope")
    (tmp_path / "notes.txt").write_text("ignored")
    assert amr.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "a.mp3  [0:03, 128 kbps, 44.1 kHz, stereo]" in out and "Title   Song" in out
    assert "broken.flac: can't read it" in out and "notes.txt" not in out
    assert "2 file(s)" in out


def test_no_files(tmp_path, capsys):
    assert amr.main([str(tmp_path)]) == 1
    assert "No audio files found" in capsys.readouterr().err
