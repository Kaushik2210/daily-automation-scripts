"""Email a report (text or HTML, with attachments) over SMTP. Previews first; --send sends."""
import argparse
import mimetypes
import os
import re
import smtplib  # web-ok: nothing is sent without --send; the preview works offline
import sys
from email.message import EmailMessage
from pathlib import Path

mimetypes.add_type("text/csv", ".csv")  # Windows would otherwise say application/vnd.ms-excel
ADDRESS = re.compile(r"^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$")
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


def check_address(value):
    if not ADDRESS.match(value):
        raise ValueError(f"not an email address: '{value}'")
    return value


def single_line(value, what):
    if "\n" in value or "\r" in value:
        raise ValueError(f"{what} can't contain line breaks")
    return value


def build_message(sender, to, cc, subject, body, html, attachments):
    """Return an EmailMessage. Attachments are paths; HTML becomes an alternative part."""
    message = EmailMessage()
    message["From"] = check_address(sender)
    message["To"] = ", ".join(check_address(a) for a in to)
    if cc:
        message["Cc"] = ", ".join(check_address(a) for a in cc)
    message["Subject"] = single_line(subject, "the subject")
    message.set_content(body)
    if html:
        message.add_alternative(html, subtype="html")
    total = 0
    for path in attachments:
        data = path.read_bytes()
        total += len(data)
        if total > MAX_ATTACHMENT_BYTES:
            raise ValueError(f"attachments are over {MAX_ATTACHMENT_BYTES // 1024 // 1024} MB")
        kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        major, _, minor = kind.partition("/")
        message.add_attachment(data, maintype=major, subtype=minor, filename=path.name)
    return message


def preview(message, recipients, bcc_count, attachments):
    lines = ["Preview (nothing sent):", ""]
    for header in ("From", "To", "Cc", "Subject"):
        if message[header]:
            lines.append(f"{header + ':':<9}{message[header]}")
    if bcc_count:
        lines.append(f"{'Bcc:':<9}{bcc_count} hidden recipient(s)")
    lines.append(f"{'Sending to:':<9} {len(recipients)} recipient(s)")
    if attachments:
        lines.append("Attachments:")
        lines += [f"  {p.name}  ({p.stat().st_size:,} bytes)" for p in attachments]
    body = message.get_body(preferencelist=("plain",)).get_content().strip().splitlines()
    lines += ["", "--- message ---"] + body[:15]
    if len(body) > 15:
        lines.append(f"... ({len(body) - 15} more line(s))")
    return "\n".join(lines)


def smtp_settings(args):
    host = args.smtp_host or os.environ.get("SMTP_HOST")
    if not host:
        raise ValueError("no SMTP server: pass --smtp-host or set SMTP_HOST")
    port = args.smtp_port or int(os.environ.get("SMTP_PORT", "465" if args.security == "ssl"
                                                else "587" if args.security == "starttls"
                                                else "25"))
    return host, port, os.environ.get("SMTP_USER"), os.environ.get(args.password_env)


def send(message, recipients, sender, host, port, security, user, password):
    if security == "ssl":
        server = smtplib.SMTP_SSL(host, port, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
    with server:
        if security == "starttls":
            import ssl  # imported here: some Python builds (and the browser) have no ssl module
            server.starttls(context=ssl.create_default_context())
        if user and password:
            server.login(user, password)
        server.send_message(message, from_addr=sender, to_addrs=recipients)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Email a report over SMTP (preview by default).")
    parser.add_argument("--to", action="append", default=[], metavar="ADDRESS", help="recipient")
    parser.add_argument("--cc", action="append", default=[], metavar="ADDRESS")
    parser.add_argument("--bcc", action="append", default=[], metavar="ADDRESS")
    parser.add_argument("--from", dest="sender",
                        help="sender (default: $REPORT_FROM or $SMTP_USER)")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body-file", type=Path, required=True, help="plain-text message body")
    parser.add_argument("--html-file", type=Path, help="optional HTML version of the body")
    parser.add_argument("--attach", action="append", default=[], type=Path, metavar="FILE")
    parser.add_argument("--smtp-host", help="SMTP server (default: $SMTP_HOST)")
    parser.add_argument("--smtp-port", type=int,
                        help="port (default: 587, 465 for ssl, 25 for none)")
    parser.add_argument("--security", choices=["starttls", "ssl", "none"], default="starttls")
    parser.add_argument("--password-env", default="SMTP_PASSWORD", metavar="NAME",
                        help="environment variable holding the SMTP password (SMTP_PASSWORD)")
    parser.add_argument("--send", action="store_true", help="really send (default only previews)")
    args = parser.parse_args(argv)
    if not args.to:
        parser.error("give at least one --to")

    sender = args.sender or os.environ.get("REPORT_FROM") or os.environ.get("SMTP_USER")
    try:
        if not sender:
            raise ValueError("no sender: pass --from or set REPORT_FROM")
        body = args.body_file.read_text(encoding="utf-8")
        html = args.html_file.read_text(encoding="utf-8") if args.html_file else None
        message = build_message(sender, args.to, args.cc, args.subject, body, html, args.attach)
        recipients = [check_address(a) for a in args.to + args.cc + args.bcc]
    except (OSError, ValueError, UnicodeDecodeError) as err:
        print(f"Can't prepare the email: {err}", file=sys.stderr)
        return 1
    if not args.send:
        print(preview(message, recipients, len(args.bcc), args.attach))
        print("\nAdd --send to deliver it.")
        return 0
    try:
        host, port, user, password = smtp_settings(args)
        send(message, recipients, sender, host, port, args.security, user, password)
    except (OSError, ValueError, smtplib.SMTPException) as err:
        print(f"Couldn't send the email: {err}", file=sys.stderr)
        return 1
    print(f"Sent to {len(recipients)} recipient(s) via {host}:{port}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
