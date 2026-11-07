import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import page_title_fetcher as pt

HTML = """<html><head><title>  My
   Page </title><meta name="Description" content="  A   short
 summary "></head><body><title>ignored in body? still title</title></body></html>"""


def test_extract_title_and_description():
    title, description = pt.extract(HTML)
    assert description == "A short summary"
    assert title == "My Page"
    assert pt.extract("<p>no head</p>") == ("", "")


def test_inspect_local_file_and_errors(tmp_path):
    f = tmp_path / "a.html"
    f.write_text("<title>Hello</title>", encoding="utf-8")
    assert pt.inspect(str(f))["title"] == "Hello"
    missing = pt.inspect(str(tmp_path / "nope.html"))
    assert missing["error"] and missing["title"] == ""
    assert pt.inspect("http://127.0.0.1:9/")["error"]


def test_cli_text_csv_and_exit_code(tmp_path, capsys):
    a, b = tmp_path / "a.html", tmp_path / "b.html"
    a.write_text('<title>Alpha</title><meta name="description" content="About A">')
    b.write_text("<p>untitled</p>")
    assert pt.main([str(a), str(b), "--description"]) == 0
    out = capsys.readouterr().out
    assert "Alpha  <-  " in out and "    About A" in out and "(no title)" in out
    assert "2 of 2 page(s) read." in out
    assert pt.main([str(a), "--csv"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == "source,title,description,error"
    assert pt.main([str(a), str(tmp_path / "missing.html")]) == 1


def test_fetch_from_a_local_server(capsys):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            body = "<title>Café Menu</title>".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/"
        assert pt.inspect(url)["title"] == "Café Menu"
    finally:
        server.shutdown()
