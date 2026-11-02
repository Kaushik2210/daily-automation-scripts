from base64_tool import decode, encode, main


def test_round_trip_standard_and_urlsafe():
    data = b"\xfb\xff\xfehello?>"
    assert decode(encode(data)) == data
    assert decode(encode(data, True), True) == data
    assert "+" in encode(b"\xfb\xff") and "-" in encode(b"\xfb\xff", True)


def test_decode_tolerates_whitespace_and_missing_padding():
    assert decode("aGVsbG8") == b"hello"
    assert decode("aGVs\nbG8=\n") == b"hello"


def test_cli_text_encode_decode(capsys):
    main(["hello world"])
    assert capsys.readouterr().out.strip() == "aGVsbG8gd29ybGQ="
    main(["--decode", "aGVsbG8gd29ybGQ="])
    assert capsys.readouterr().out.strip() == "hello world"


def test_invalid_input_and_binary_result(capsys):
    assert main(["--decode", "a"]) == 1
    assert "Not valid Base64" in capsys.readouterr().err
    assert main(["--decode", "/+8="]) == 1
    assert "binary data" in capsys.readouterr().err


def test_file_to_file_needs_apply(tmp_path):
    src, out, back = tmp_path / "a.bin", tmp_path / "a.b64", tmp_path / "back.bin"
    src.write_bytes(b"\x00\x01\x02binary")
    main(["-f", str(src), "-o", str(out)])
    assert not out.exists()
    main(["-f", str(src), "-o", str(out), "--apply"])
    main(["-d", "-f", str(out), "-o", str(back), "--apply"])
    assert back.read_bytes() == src.read_bytes()
