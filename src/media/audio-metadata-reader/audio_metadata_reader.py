"""Read tags and duration from audio files (MP3, FLAC and WAV) without any extra library."""
import argparse
import struct
import sys
import wave
from pathlib import Path

EXTENSIONS = {".mp3", ".flac", ".wav"}
ID3_FRAMES = {"TIT2": "title", "TPE1": "artist", "TALB": "album", "TYER": "year", "TDRC": "year",
              "TRCK": "track", "TCON": "genre"}
ID3V1_GENRES = {0: "Blues", 1: "Classic Rock", 2: "Country", 7: "Hip-Hop", 8: "Jazz", 9: "Metal",
                13: "Pop", 17: "Rock", 32: "Classical"}
BITRATES = {  # MPEG1 Layer III and MPEG2/2.5 Layer III, in kbit/s (index 1..14)
    1: [32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
    2: [8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]}
SAMPLE_RATES = {1: [44100, 48000, 32000], 2: [22050, 24000, 16000], 25: [11025, 12000, 8000]}


def decode_text(raw):
    """Decode an ID3 text frame body (first byte says which encoding)."""
    if not raw:
        return ""
    encoding, body = raw[0], raw[1:]
    codec = {0: "latin-1", 1: "utf-16", 2: "utf-16-be", 3: "utf-8"}.get(encoding, "latin-1")
    return body.decode(codec, errors="replace").strip("\x00 ").split("\x00")[0]


def read_id3v2(data):
    """Return (tags, size of the tag including its header)."""
    if data[:3] != b"ID3" or len(data) < 10:
        return {}, 0
    version = data[3]
    size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
    tags, offset, end = {}, 10, min(10 + size, len(data))
    while offset + 10 <= end:
        frame_id = data[offset:offset + 4].decode("latin-1")
        if not frame_id.strip("\x00"):
            break
        raw_size = data[offset + 4:offset + 8]
        length = (int.from_bytes(raw_size, "big") if version == 3 else
                  (raw_size[0] << 21) | (raw_size[1] << 14) | (raw_size[2] << 7) | raw_size[3])
        body = data[offset + 10:offset + 10 + length]
        if frame_id in ID3_FRAMES:
            tags.setdefault(ID3_FRAMES[frame_id], decode_text(body))
        offset += 10 + length
    return tags, 10 + size


def read_id3v1(data):
    if len(data) < 128 or data[-128:-125] != b"TAG":
        return {}
    block = data[-128:]

    def text(a, b):
        return block[a:b].split(b"\x00")[0].decode("latin-1").strip()
    tags = {"title": text(3, 33), "artist": text(33, 63), "album": text(63, 93),
            "year": text(93, 97)}
    if block[125] == 0 and block[126]:
        tags["track"] = str(block[126])
    if block[127] in ID3V1_GENRES:
        tags["genre"] = ID3V1_GENRES[block[127]]
    return {key: value for key, value in tags.items() if value}


def mp3_audio(data, start):
    """Find the first MPEG frame; return (bitrate_kbps, sample_rate, channels) or None."""
    for pos in range(start, min(len(data) - 4, start + 4096)):
        if data[pos] == 0xFF and data[pos + 1] & 0xE0 == 0xE0:
            header = struct.unpack(">I", data[pos:pos + 4])[0]
            version = {3: 1, 2: 2, 0: 25}.get((header >> 19) & 3)
            layer, bitrate_index = (header >> 17) & 3, (header >> 12) & 15
            rate_index = (header >> 10) & 3
            if version is None or layer != 1 or not 1 <= bitrate_index <= 14 or rate_index == 3:
                continue
            bitrate = BITRATES[1 if version == 1 else 2][bitrate_index - 1]
            channels = 1 if (header >> 6) & 3 == 3 else 2
            return bitrate, SAMPLE_RATES[version][rate_index], channels
    return None


def read_mp3(data):
    tags, tag_size = read_id3v2(data)
    v1 = read_id3v1(data)
    for key, value in v1.items():
        tags.setdefault(key, value)
    info = {"tags": tags}
    audio = mp3_audio(data, tag_size)
    if audio:
        bitrate, rate, channels = audio
        payload = len(data) - tag_size - (128 if v1 else 0)
        info.update(duration=payload * 8 / (bitrate * 1000), bitrate=bitrate,
                    sample_rate=rate, channels=channels)
    return info


def read_flac(data):
    if data[:4] != b"fLaC":
        raise ValueError("not a FLAC file")
    info, offset, last = {"tags": {}}, 4, False
    while not last and offset + 4 <= len(data):
        last, kind = bool(data[offset] & 0x80), data[offset] & 0x7F
        length = int.from_bytes(data[offset + 1:offset + 4], "big")
        block = data[offset + 4:offset + 4 + length]
        if kind == 0 and len(block) >= 18:
            packed = int.from_bytes(block[10:18], "big")
            rate, channels = packed >> 44, ((packed >> 41) & 7) + 1
            bits, total = ((packed >> 36) & 31) + 1, packed & 0xFFFFFFFFF
            info.update(sample_rate=rate, channels=channels, bits=bits,
                        duration=total / rate if rate else None)
        elif kind == 4:
            vendor = struct.unpack("<I", block[:4])[0]
            position = 8 + vendor
            for _ in range(struct.unpack("<I", block[4 + vendor:8 + vendor])[0]):
                size = struct.unpack("<I", block[position:position + 4])[0]
                text = block[position + 4:position + 4 + size].decode("utf-8", errors="replace")
                key, _, value = text.partition("=")
                name = {"tracknumber": "track", "date": "year"}.get(key.lower(), key.lower())
                info["tags"].setdefault(name, value)
                position += 4 + size
        offset += 4 + length
    return info


def read_wav(path):
    with wave.open(str(path), "rb") as audio:
        rate = audio.getframerate()
        return {"tags": {}, "duration": audio.getnframes() / rate, "sample_rate": rate,
                "channels": audio.getnchannels(), "bits": audio.getsampwidth() * 8}


def read_audio(path):
    data = path.read_bytes() if path.suffix.lower() != ".wav" else b""
    kind = path.suffix.lower()
    if kind == ".mp3":
        return read_mp3(data)
    if kind == ".flac":
        return read_flac(data)
    return read_wav(path)


def clock(seconds):
    seconds = round(seconds)
    hours, rest = divmod(seconds, 3600)
    return f"{hours}:{rest // 60:02d}:{rest % 60:02d}" if hours else f"{rest // 60}:{rest % 60:02d}"


def describe(info):
    parts = []
    if info.get("duration") is not None:
        parts.append(clock(info["duration"]))
    if info.get("bitrate"):
        parts.append(f"{info['bitrate']} kbps")
    if info.get("sample_rate"):
        parts.append(f"{info['sample_rate'] / 1000:g} kHz")
    if info.get("channels"):
        parts.append({1: "mono", 2: "stereo"}.get(info["channels"], f"{info['channels']} channels"))
    return ", ".join(parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read audio tags and duration.")
    parser.add_argument("paths", nargs="+", type=Path, help="audio files or folders")
    args = parser.parse_args(argv)

    files = []
    for path in args.paths:
        if path.is_dir():
            files += sorted(p for p in path.iterdir() if p.suffix.lower() in EXTENSIONS)
        elif path.is_file():
            files.append(path)
        else:
            print(f"not found: {path}", file=sys.stderr)
    if not files:
        print("No audio files found.", file=sys.stderr)
        return 1
    failures, total = 0, 0.0
    for path in files:
        try:
            info = read_audio(path)
        except (OSError, ValueError, wave.Error, struct.error, EOFError) as err:
            print(f"{path.name}: can't read it ({err})")
            failures += 1
            continue
        tags = info["tags"]
        total += info.get("duration") or 0
        print(f"{path.name}  [{describe(info) or 'no audio details'}]")
        for key in ("title", "artist", "album", "year", "track", "genre"):
            if tags.get(key):
                print(f"    {key.capitalize():<7} {tags[key]}")
        if not tags:
            print("    (no tags)")
    print(f"\n{len(files) - failures} file(s), {clock(total)} in total.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
