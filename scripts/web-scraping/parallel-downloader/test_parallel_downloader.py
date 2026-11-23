import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import parallel_downloader as pd
import pytest

DATA = bytes(range(256)) * 400  # 102,400 bytes


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/missing"):
            self.send_response(404)
            self.end_headers()
            return
        data, start = DATA, 0
        header = self.headers.get("Range")
        if header and self.path.startswith("/file") and header.startswith("bytes="):
            start = int(header[6:].split("-")[0])
            if start >= len(data):
                self.send_response(416)
                self.end_headers()
                return
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(data) - 1}/{len(data)}")
        else:
            self.send_response(200)  # /norange ignores Range requests
        self.send_header("Content-Length", str(len(data) - start))
        self.end_headers()
        self.wfile.write(data[start:])


@pytest.fixture
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.mark.parametrize("url,name", [
    ("https://x.org/reports/q3%20final.pdf", "q3 final.pdf"),
    ("https://x.org/a/b/", "b"), ("https://x.org/", "download-"), ("https://x.org/dl?id=7", "dl-"),
    ("https://x.org/get?id=7", "get-"), ("https://x.org/f.zip?x=1", "f.zip"),
    ("https://x.org/we:ird*.txt", "we_ird_.txt")])
def test_file_name(url, name):
    assert pd.file_name(url).startswith(name)


def test_unique_names_for_colliding_urls():
    names = pd.unique_names(["https://a.org/x/report.pdf", "https://b.org/y/report.pdf",
                             "https://c.org/REPORT.pdf"])
    assert list(names.values()) == ["report.pdf", "report (1).pdf", "REPORT (2).pdf"]


def test_read_urls(tmp_path):
    listing = tmp_path / "u.txt"
    listing.write_text("# c\nhttps://a.org/f\nftp://x\nhttps://a.org/f\nnot a url\n")
    assert pd.read_urls([str(listing), "http://b.org/g"]) == (
        ["https://a.org/f", "http://b.org/g"], ["ftp://x", "not a url"])


def test_state_of(tmp_path):
    (tmp_path / "done.bin").write_bytes(b"x")
    (tmp_path / "half.bin.part").write_bytes(b"abc")
    (tmp_path / "empty.bin.part").write_bytes(b"")
    assert pd.state_of(tmp_path, "done.bin") == ("done", 0)
    assert pd.state_of(tmp_path, "half.bin") == ("resume", 3)
    assert pd.state_of(tmp_path, "empty.bin") == ("new", 0)


def test_download_whole_file_and_atomic_rename(server, tmp_path):
    size, resumed = pd.download(f"{server}/file.bin", tmp_path, "f.bin", 5, 0)
    assert (size, resumed) == (len(DATA), False)
    assert (tmp_path / "f.bin").read_bytes() == DATA and not (tmp_path / "f.bin.part").exists()


def test_resume_continues_from_the_part_file(server, tmp_path):
    (tmp_path / "f.bin.part").write_bytes(DATA[:30000])
    size, resumed = pd.download(f"{server}/file.bin", tmp_path, "f.bin", 5, 0)
    assert resumed and (tmp_path / "f.bin").read_bytes() == DATA and size == len(DATA)


def test_server_without_range_support_restarts_cleanly(server, tmp_path):
    (tmp_path / "f.bin.part").write_bytes(b"garbage" * 100)
    size, resumed = pd.download(f"{server}/norange", tmp_path, "f.bin", 5, 0)
    assert not resumed and (tmp_path / "f.bin").read_bytes() == DATA


def test_complete_part_file_is_accepted_on_416(server, tmp_path):
    (tmp_path / "f.bin.part").write_bytes(DATA)
    size, resumed = pd.download(f"{server}/file.bin", tmp_path, "f.bin", 5, 0)
    assert resumed and size == len(DATA) and (tmp_path / "f.bin").exists()


def test_http_errors_are_reported(server, tmp_path):
    with pytest.raises(OSError, match="HTTP 404"):
        pd.download(f"{server}/missing", tmp_path, "m.bin", 5, 0)


def test_cli_plan_then_apply(server, tmp_path, capsys):
    out = tmp_path / "dl"
    out.mkdir()
    (out / "have.bin").write_bytes(b"x")
    (out / "part.bin.part").write_bytes(DATA[:10])
    urls = [f"{server}/file/new.bin", f"{server}/file/part.bin", f"{server}/file/have.bin",
            f"{server}/missing/gone.bin"]
    assert pd.main([*urls, "-o", str(out)]) == 0
    plan = capsys.readouterr().out
    assert "new.bin" in plan and "resume from 10 B" in plan and "exists, skipped" in plan
    assert "Dry run: 3 to download" in plan and not (out / "new.bin").exists()
    assert pd.main([*urls, "-o", str(out), "--apply", "--retries", "0"]) == 1
    result = capsys.readouterr().out
    assert "done  new.bin" in result and "resumed" in result
    assert "FAIL  gone.bin: HTTP 404" in result
    assert (out / "new.bin").read_bytes() == DATA and (out / "part.bin").read_bytes() == DATA
    assert (out / "have.bin").read_bytes() == b"x"  # never overwritten
    assert "2 downloaded, 1 failed." in result


def test_no_valid_urls(capsys):
    assert pd.main(["ftp://x/y"]) == 1
    assert "No valid" in capsys.readouterr().err
