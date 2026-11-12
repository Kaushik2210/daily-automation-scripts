import pytest
import status_code_counter as scc


def line(status, path="/", method="GET"):
    stamp = "[10/Nov/2026:09:00:00 +0000]"
    return f'1.2.3.4 - - {stamp} "{method} {path} HTTP/1.1" {status} 100 "-" "ua"'


LINES = [line(200), line(200, "/a"), line(200, "/a?x=1"), line(404, "/missing"),
         line(404, "/missing?ref=2"), line(404, "/other"), line(500, "/api/orders", "POST"),
         line(301, "/old"), line(418, "/teapot"), "garbage line", ""]


def test_parse_line_strips_query_strings_and_rejects_garbage():
    assert scc.parse_line(line(404, "/x?y=1")) == (404, "GET", "/x")
    assert scc.parse_line('1.2.3.4 - - [10/Nov/2026:09:00:00 +0000] "-" 400 0') == (400, "", "")
    assert scc.parse_line("garbage") is None


def test_reason_phrases():
    assert [scc.reason(c) for c in (200, 404, 500, 418, 799)] == [
        "OK", "Not Found", "Internal Server Error", "I'm a Teapot", "unknown"]


def test_count_codes_paths_and_bad_lines():
    codes, paths, bad = scc.count(LINES)
    assert codes == {200: 3, 404: 3, 500: 1, 301: 1, 418: 1} and bad == 1
    assert paths[404].most_common(1) == [("/missing", 2)]


def test_count_filters():
    codes, _, _ = scc.count(LINES, method="post")
    assert codes == {500: 1}
    codes, _, _ = scc.count(LINES, path_contains="/a")
    assert codes == {200: 2, 500: 1}  # "/a", "/a?x=1" and "/api/orders" contain "/a"


def test_report_layout(tmp_path, capsys):
    path = tmp_path / "access.log"
    path.write_text("\n".join(LINES))
    assert scc.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("9 request(s); 1 unreadable line(s) skipped")
    assert "404 Not Found" in out and "33.3%" in out
    assert "4xx client error" in out and "5xx server error" in out
    assert "404: /missing (2), /other (1)" in out and "500: /api/orders (1)" in out
    assert "Client errors: 44.4%   Server errors: 11.1%" in out


def test_top_paths_can_be_hidden(tmp_path, capsys):
    path = tmp_path / "access.log"
    path.write_text("\n".join(LINES))
    assert scc.main([str(path), "--top-paths", "0"]) == 0
    assert "Paths behind the errors" not in capsys.readouterr().out


def test_failure_threshold_for_server_errors(tmp_path, capsys):
    path = tmp_path / "access.log"
    path.write_text("\n".join(LINES))
    assert scc.main([str(path), "--fail-above-5xx", "20"]) == 0
    assert scc.main([str(path), "--fail-above-5xx", "5"]) == 1
    assert "above the limit of 5%" in capsys.readouterr().out


def test_empty_and_missing_inputs(tmp_path, capsys):
    path = tmp_path / "none.log"
    path.write_text("nothing here\n")
    assert scc.main([str(path)]) == 1
    assert scc.main([str(tmp_path / "gone.log")]) == 1
    with pytest.raises(SystemExit):
        scc.main([str(path), "--top-paths", "-1"])
