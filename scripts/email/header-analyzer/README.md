# header-analyzer

## Purpose
See where an email really came from. The tool reads a saved message (an `.eml` file, or just its headers pasted into a text file) and lays out the route it took, one hop per `Received` line from the sender's server to yours, with the time each hop took. It also reports the SPF, DKIM and DMARC verdicts your mail provider recorded and flags things that deserve a second look.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python header_analyzer.py message.eml
```
In most mail apps you can save the original message with "Download message", "Show original" or "View source". Warnings cover failed SPF/DKIM/DMARC checks, a Return-Path or Reply-To on a different domain from the sender, missing authentication results, and slow or out-of-order hops. The exit code is 1 when there is at least one warning.

## Example
```bash
python header_analyzer.py message.eml
```
```
From:       Daily Brief <news@brief.example>
To:         Sam Reader <sam@example.org>
Subject:    Your Monday brief
Date:       Mon, 02 Nov 2026 07:29:00 +0000
Message-ID: <brief-1102@brief.example>

Route (3 hop(s), oldest first):
  1. app01.brief.example -> relay.brief.example   2026-11-02 07:29:02 +0000
  2. relay.brief.example -> mx1.example.org   2026-11-02 07:30:05 +0000  (+63s)
  3. mx1.example.org -> inbox.example.org   2026-11-02 07:30:09 +0000  (+4s)
  total transit: 67 seconds

Authentication:
  SPF   pass
  DKIM  pass
  DMARC fail
  signed by brief.example

Warnings:
  ! DMARC result is 'fail'
```

## Notes
- Everything is read from the file; nothing is sent over the network.
- Headers can be forged by the original sender. Only the topmost `Received` lines, added by servers you trust, are reliable.
- Newsletters often send from a sub-domain (such as `mailer.brand.example`); that counts as aligned and isn't flagged.
- If your provider doesn't record `Authentication-Results`, the tool falls back to the `Received-SPF` header.
