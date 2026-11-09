# eml-to-text

## Purpose
Read saved emails without a mail program. The tool converts `.eml` files (the format you get from "save as" or "download message") into plain text: the main header lines, the readable body (plain text when there is one, otherwise the HTML turned into text with links kept), and a list of attachment names. It works on single files or whole folders.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python eml_to_text.py PATH [PATH ...] [--width 80] [--out-dir DIR] [--apply]
```
By default the text is printed. With `--out-dir` it shows which `.txt` files it would write; add `--apply` to create them. Existing files are never overwritten: a copy gets a number (`message-2.txt`).

## Example
```bash
python eml_to_text.py message.eml --width 60
```
```
From: Daily Brief <news@brief.example>
To: Sam Reader <sam@example.org>
Date: Mon, 02 Nov 2026 07:29:00 +0000
Subject: Your Monday brief

Good morning!

Here is your Monday brief.

- Council approves budget - Bridge reopens

Unsubscribe: https://brief.example/unsub?u=1
```

## Notes
- Attachments aren't extracted, only listed by name.
- Remote images and tracking pixels in HTML mail are ignored, and nothing is fetched from the network.
- Messages with several languages or odd encodings are decoded using the charset they declare; broken ones may show replacement characters.
- On the website demo, saved files are written to your browser's temporary folder.
