import json
import shutil
import subprocess

import docker_image_reporter as dir_
import pytest


def row(repo, tag, size, since="2 days ago", image_id="abcdef1234567890"):
    return json.dumps({"Repository": repo, "Tag": tag, "Size": size, "CreatedSince": since,
                       "ID": image_id})


LIST = "\n".join([row("python", "3.12", "1.02GB"), row("alpine", "3.20", "7.8MB"),
                  row("<none>", "<none>", "212MB"), row("myapp", "latest", "845MB"),
                  row("myapp", "1.0", "843MB"), row("hello", "latest", "13.3kB")])


@pytest.mark.parametrize("text,size", [("1.02GB", 1_020_000_000), ("245MB", 245_000_000),
                                       ("12.3kB", 12_300), ("0B", 0), ("7.8 MB", 7_800_000)])
def test_to_bytes(text, size):
    assert dir_.to_bytes(text) == size


@pytest.mark.parametrize("bad", ["", "big", "12XB", "GB"])
def test_to_bytes_rejects_nonsense(bad):
    with pytest.raises(ValueError):
        dir_.to_bytes(bad)


def test_human():
    assert dir_.human(512) == "512 B" and dir_.human(13_300) == "13.3 kB"
    assert dir_.human(1_020_000_000) == "1.0 GB"


def test_parse_images():
    images = dir_.parse_images(LIST + "\n\n")
    assert len(images) == 6 and images[0]["name"] == "python:3.12"
    assert images[2]["name"] == "<none>" and images[0]["id"] == "abcdef123456"


def test_cli_report(tmp_path, capsys):
    path = tmp_path / "images.jsonl"
    path.write_text(LIST)
    assert dir_.main(["--from-file", str(path), "--top", "3"]) == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert lines[1].startswith("python:3.12") and "<- large" in lines[1]
    assert lines[2].startswith("myapp:latest") and lines[3].startswith("myapp:1.0")
    assert "... and 3 more" in out and "6 image(s), 2.9 GB in total" in out
    assert "1 dangling image(s) using 212.0 MB" in out
    assert "myapp has 2 tags (latest, 1.0) totalling 1.7 GB" in out


def test_bad_and_empty_input(tmp_path, capsys):
    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not json")
    assert dir_.main(["--from-file", str(bad)]) == 1
    assert "Can't read the image list" in capsys.readouterr().err
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    assert dir_.main(["--from-file", str(empty)]) == 0
    assert "No images found." in capsys.readouterr().out


def test_docker_not_installed_and_fake_docker(monkeypatch, capsys):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert dir_.main([]) == 1
    assert "docker was not found" in capsys.readouterr().err
    monkeypatch.setattr(shutil, "which", lambda name: "/bin/docker")
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(
        cmd, 0, row("redis", "7", "117MB"), ""))
    assert dir_.main([]) == 0
    assert "redis:7" in capsys.readouterr().out
