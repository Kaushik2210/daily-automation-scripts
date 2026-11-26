# email-report-sender

## Purpose
Email a report, as plain text with an optional HTML version and attachments, over SMTP. It shows
a preview of exactly what would go out and only sends when you add `--send`.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python email_report_sender.py --to team@example.com --from me@example.com \
    --subject "Weekly report" --body-file report.txt --attach report.pdf
python email_report_sender.py ... --send
python email_report_sender.py ... --html-file report.html --cc boss@example.com --send
```

SMTP settings come from the environment, so no secret goes on the command line or into a file:

| Variable | Meaning |
|---|---|
| `SMTP_HOST` | the SMTP server (or pass `--smtp-host`) |
| `SMTP_PORT` | port; defaults to 587 (starttls), 465 (ssl) or 25 (none) |
| `SMTP_USER` | login name, also used as the sender if `--from` is missing |
| `SMTP_PASSWORD` | password; use `--password-env NAME` to read another variable |
| `REPORT_FROM` | default sender |

`--security` picks `starttls` (default), `ssl` or `none`. `--bcc` recipients get the mail but are
never written into the message headers. Attachments are limited to 10 MB in total. The password
is never printed.

## Example
`--to team@example.com --from reports@example.com --subject "Weekly report" --body-file report-body.txt --attach report-sections/02-results.md`

```
Preview (nothing sent):

From:    reports@example.com
To:      team@example.com
Subject: Weekly report
Sending to: 1 recipient(s)
Attachments:
  02-results.md  (138 bytes)

--- message ---
Hello team,

Here is this week's summary.

- 2 releases shipped
- Open bugs down to 9
- P95 latency 280 ms

Full details are in the attached report.

Thanks,
Platform team

Add --send to deliver it.
```

## Notes
- Addresses are checked, and subjects or addresses containing line breaks are refused, so a
  report title can't be used to inject extra headers.
- The browser demo only shows the preview. Sending needs a real SMTP server.
- Tested against a local fake SMTP server, not against a real mail provider.
