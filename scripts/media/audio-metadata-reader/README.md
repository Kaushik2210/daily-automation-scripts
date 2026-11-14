# audio-metadata-reader

## Purpose
Find out what is inside your music files without opening a player: title, artist, album, year, track number, genre and the length of each file, plus bitrate, sample rate and channels. It reads MP3 (ID3v2 and ID3v1 tags), FLAC (Vorbis comments) and WAV files with the Python standard library alone, so there is nothing to install.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python audio_metadata_reader.py FILE_OR_FOLDER [FILE_OR_FOLDER ...]
```
Folders are scanned for `.mp3`, `.flac` and `.wav` files (not subfolders). The exit code is 1 if any file couldn't be read. The last line adds up the total playing time, handy for an album or a playlist folder.

## Example
```bash
python audio_metadata_reader.py audio-demo/
```
```
morning-raga.mp3  [0:03, 128 kbps, 44.1 kHz, stereo]
    Title   Morning Raga
    Artist  Demo Quartet
    Album   Sunrise Sessions
    Year    2025
    Track   3/9
    Genre   Classical
night-drive.flac  [3:20, 44.1 kHz, stereo]
    Title   Night Drive
    Artist  Synth Collective
    Album   Neon Roads
    Year    2024
    Track   1
    Genre   Electronic
tone.wav  [0:02, 8 kHz, mono]
    (no tags)

3 file(s), 3:25 in total.
```

## Notes
- MP3 length is worked out from the file size and the first frame's bitrate, so it is exact for constant-bitrate files and an estimate for variable-bitrate ones.
- Other formats (M4A, OGG, Opus) aren't supported; use `video-info-reporter` (via ffprobe) for those.
- The tool only reads; it never changes tags. Use a tag editor such as Mp3tag or MusicBrainz Picard to edit them.
