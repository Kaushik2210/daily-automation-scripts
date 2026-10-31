import json

import python_env_reporter as per


def test_installed_packages_is_sorted_and_includes_pytest():
    packages = per.installed_packages()
    names = [n.lower() for n in packages]
    assert names == sorted(names)
    assert "pytest" in names


def test_filter_and_requirements():
    packages = {"Alpha": "1.0", "beta-tools": "2.1", "gamma": "0.3"}
    assert per.filter_packages(packages, "TOOLS") == {"beta-tools": "2.1"}
    assert per.as_requirements({"a": "1", "b": "2"}) == "a==1\nb==2"


def test_json_output(capsys):
    per.main(["pytest", "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert "pytest" in {n.lower() for n in data["packages"]}
    assert data["python"].count(".") == 2


def test_table_output_has_summary(capsys):
    per.main(["pytest"])
    out = capsys.readouterr().out
    assert out.startswith("Python ") and "package(s)." in out
