import io
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import breach_password_checker as bpc
import pytest

PASSWORD_HASH = "5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8"  # SHA-1 of the word "password"


def test_sha1_and_split():
    assert bpc.sha1_of("password") == PASSWORD_HASH
    assert bpc.split_hash(PASSWORD_HASH) == ("5BAA6", PASSWORD_HASH[5:])


def test_count_in_range_ignores_padding_case_and_junk():
    text = "\n".join([PASSWORD_HASH[5:] + ":9545824", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA:0",
                      "not a line", "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB:12"])
    assert bpc.count_in_range(text, PASSWORD_HASH[5:]) == 9545824
    assert bpc.count_in_range(text, PASSWORD_HASH[5:].lower()) == 9545824
    assert bpc.count_in_range(text, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA") == 0  # padding entry
    assert bpc.count_in_range(text, "C" * 35) == 0 and bpc.count_in_range("", "X") == 0


def test_describe():
    assert "Not found" in bpc.describe(0)
    assert "1 time in data breaches" in bpc.describe(1)
    assert "9,545,824 times" in bpc.describe(9545824)


def write_range(tmp_path, count=1234):
    path = tmp_path / "range.txt"
    path.write_text(f"{PASSWORD_HASH[5:]}:{count}\n0018A45C4D1DEF81644B54AB7F969B88D65:10\n")
    return str(path)


def test_cli_with_a_saved_range_for_a_hash(tmp_path, capsys):
    assert bpc.main(["--sha1", PASSWORD_HASH.lower(), "--range-file", write_range(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "Checked hash prefix 5BAA6...." in out and "appeared 1,234 times" in out
    assert PASSWORD_HASH not in out and PASSWORD_HASH[5:] not in out  # never prints the hash


def test_cli_clean_password_from_stdin(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bpc.sys, "stdin", io.StringIO("a-long-unique-passphrase-7731\n"))
    assert bpc.main(["--stdin", "--range-file", write_range(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "Not found in any known breach" in out and "a-long-unique" not in out


def test_the_password_is_found_when_typed_at_the_prompt(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bpc.getpass, "getpass", lambda prompt: "password")
    assert bpc.main(["--range-file", write_range(tmp_path)]) == 1
    assert "FOUND" in capsys.readouterr().out


def test_empty_password_and_bad_hash(monkeypatch, capsys):
    monkeypatch.setattr(bpc.sys, "stdin", io.StringIO("\n"))
    assert bpc.main(["--stdin"]) == 1
    assert "No password given." in capsys.readouterr().err
    with pytest.raises(SystemExit):
        bpc.main(["--sha1", "not-a-hash"])
    with pytest.raises(SystemExit):
        bpc.main(["--sha1", "ab" * 21])


class Handler(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        Handler.seen.append((self.path, self.headers.get("Add-Padding")))
        if self.path == "/range/5BAA6":
            body = f"{PASSWORD_HASH[5:]}:42\nFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:0\n"
            self.send_response(200)
        else:
            body = "00000000000000000000000000000000000:3\n"
            self.send_response(200)
        self.end_headers()
        self.wfile.write(body.encode())


@pytest.fixture
def server(monkeypatch):
    Handler.seen = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(bpc, "API", f"http://127.0.0.1:{httpd.server_address[1]}/range/")
    yield httpd
    httpd.shutdown()


def test_live_check_sends_only_the_five_character_prefix(server, monkeypatch, capsys):
    monkeypatch.setattr(bpc.getpass, "getpass", lambda prompt: "password")
    assert bpc.main([]) == 1
    assert Handler.seen == [("/range/5BAA6", "true")]
    assert "appeared 42 times" in capsys.readouterr().out


def test_network_failure_is_reported(monkeypatch, capsys):
    def boom(prefix, timeout):
        raise OSError("no network")

    monkeypatch.setattr(bpc, "fetch_range", boom)
    assert bpc.main(["--sha1", PASSWORD_HASH]) == 1
    assert "Couldn't get the range for 5BAA6" in capsys.readouterr().err
