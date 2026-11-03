# qr-generator

## Purpose
Turn a web address, Wi-Fi details or any short text into a QR code. It draws the code right in the terminal and can also save it as an SVG (sharp at any size) or PNG file.

## Install
Needs the `qrcode` package (PNG output also uses Pillow):
```bash
pip install -r requirements.txt
```

## Usage
```bash
python qr_generator.py TEXT [--level L|M|Q|H] [--ascii] [-o FILE.svg|FILE.png --apply]
```
The code is always printed. To save a file, pass `-o` together with `--apply`; the extension picks the format. Higher error-correction levels survive more damage but make the code denser.

## Example
```bash
python qr_generator.py "https://example.com" --ascii
```
```
QR version 2, 29 modules wide, level M.
```
(The code itself is drawn above that line.)

## Notes
- Scan the result with a phone before printing or sharing it.
- `--ascii` uses `##` characters, which works in any terminal; the default block characters are more compact.
- SVG output needs no image library; PNG output needs Pillow.
