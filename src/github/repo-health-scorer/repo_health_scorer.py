"""Score a project folder on what makes a repo trustworthy: README, license, tests, CI..."""
import argparse
import fnmatch
import re
import subprocess  # web-ok: git is only run with --git to read the last commit date
import sys
from datetime import date, datetime
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".idea", ".vscode", "dist",
             "build", ".tox", ".mypy_cache", ".pytest_cache", "target"}
JUNK = {"node_modules", "__pycache__", ".DS_Store", ".env", "Thumbs.db"}
CI_FILES = [".gitlab-ci.yml", ".travis.yml", "azure-pipelines.yml", "Jenkinsfile", "appveyor.yml",
            ".drone.yml", "bitbucket-pipelines.yml"]
MANIFESTS = ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile", "package.json",
             "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "Gemfile", "composer.json"]


def find(root, *names):
    """First existing file in the root whose name (case-insensitive, any extension) matches."""
    wanted = {n.lower() for n in names}
    for path in sorted(root.iterdir()):
        if path.is_file() and (path.name.lower() in wanted or path.stem.lower() in wanted):
            return path
    return None


def scan(root):
    """Collect the facts about the folder."""
    files, dirs, junk = [], [], []
    ignore = root / ".gitignore"
    ignored = [ln.strip().strip("/") for ln in ignore.read_text(encoding="utf-8",
                                                               errors="replace").splitlines()
               if ln.strip() and not ln.startswith("#")] if ignore.is_file() else []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts[:-1]) or (
                path.is_dir() and path.name in SKIP_DIRS and path.name not in JUNK):
            continue
        looks_junk = path.name in JUNK or path.suffix == ".pyc"
        if looks_junk and not any(fnmatch.fnmatch(path.name, pat) for pat in ignored):
            junk.append(relative.as_posix())  # junk that .gitignore already hides doesn't count
        (dirs if path.is_dir() else files).append(relative)
    names = {f.as_posix() for f in files}
    readme = find(root, "readme")
    text = readme.read_text(encoding="utf-8", errors="replace") if readme else ""
    heading = re.compile(r"^#{1,6}\s+(.+?)\s*#*$", re.MULTILINE)
    headings = [m.group(1).lower() for m in heading.finditer(text)]
    tests = [f for f in files if re.search(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*\.py$|"
                                           r"_test\.(py|go)$|\.(test|spec)\.[jt]sx?$",
                                           f.as_posix())]
    workflows = [f for f in files if f.as_posix().startswith(".github/workflows/")]
    return {"readme": readme.name if readme else None, "readme_words": len(text.split()),
            "readme_headings": headings, "license": find(root, "license", "licence", "copying"),
            "tests": tests, "ci": workflows or [f for f in files if f.name in CI_FILES],
            "gitignore": ".gitignore" in names,
            "manifest": next((m for m in MANIFESTS if m in names), None),
            "contributing": find(root, "contributing"), "changelog": find(root, "changelog",
                                                                           "changes", "history"),
            "community": find(root, "security", "code_of_conduct"), "junk": junk,
            "file_count": len(files)}


def score(facts, days_since_commit=None):
    """Return [(name, points, maximum, advice)] for each check."""
    has = bool
    sections = " ".join(facts["readme_headings"])
    checks = [
        ("README", 10 * has(facts["readme"]), 10, "Add a README.md explaining what the project is"),
        ("README detail", 5 * (facts["readme_words"] >= 100), 5,
         "Expand the README (at least ~100 words)"),
        ("README install/usage", 5 * bool(re.search(r"install|usage|getting started|quick",
                                                    sections)), 5,
         "Add Install and Usage sections to the README"),
        ("License", 10 * has(facts["license"]), 10, "Add a LICENSE file (choosealicense.com)"),
        ("Tests", 15 * has(facts["tests"]), 15, "Add automated tests (a tests/ folder)"),
        ("CI", 15 * has(facts["ci"]), 15, "Run the tests on every push (e.g. GitHub Actions)"),
        (".gitignore", 5 * facts["gitignore"], 5, "Add a .gitignore so build files stay out"),
        ("Dependencies listed", 5 * has(facts["manifest"]), 5,
         "List dependencies (requirements.txt, pyproject.toml, package.json...)"),
        ("CONTRIBUTING", 5 * has(facts["contributing"]), 5, "Add CONTRIBUTING.md for newcomers"),
        ("CHANGELOG", 5 * has(facts["changelog"]), 5, "Keep a CHANGELOG.md of notable changes"),
        ("SECURITY / conduct", 5 * has(facts["community"]), 5,
         "Add SECURITY.md or CODE_OF_CONDUCT.md"),
        ("No junk committed", 5 * (not facts["junk"]), 5,
         "Remove committed junk: " + ", ".join(facts["junk"][:3])),
    ]
    if days_since_commit is not None:
        fresh = 10 if days_since_commit <= 90 else 5 if days_since_commit <= 365 else 0
        checks.append(("Recent activity", fresh, 10,
                       f"The last commit was {days_since_commit} days ago"))
    return checks


def grade(percent):
    return next(g for floor, g in [(90, "A"), (75, "B"), (60, "C"), (40, "D"), (0, "F")]
                if percent >= floor)


def last_commit_age(root, today=None):
    if not (root / ".git").exists():  # only the folder's own history counts, not a parent repo's
        return None
    result = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%cs"],
                            capture_output=True, text=True, timeout=30, check=False)
    if result.returncode or not result.stdout.strip():
        return None
    return ((today or date.today()) - datetime.strptime(result.stdout.strip(), "%Y-%m-%d").date()
            ).days


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score a repository folder's health.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--git", action="store_true", help="also score the last commit's age")
    parser.add_argument("--min-score", type=int, default=60, help="exit with 1 below this % (60)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    age = None
    if args.git:
        try:
            age = last_commit_age(args.folder)
        except (OSError, subprocess.SubprocessError):
            age = None
        if age is None:
            print("(No git history found, so recent activity isn't scored.)")
    facts = scan(args.folder)
    checks = score(facts, age)
    points, total = sum(c[1] for c in checks), sum(c[2] for c in checks)
    percent = round(100 * points / total)
    print(f"{args.folder.resolve().name}: {facts['file_count']} file(s), health {percent}% "
          f"(grade {grade(percent)})\n")
    for name, got, most, advice in checks:
        mark = "PASS" if got == most else "PART" if got else "MISS"
        print(f"  [{mark}] {name:<22} {got:>2}/{most:<2}" + ("" if got == most else f"  {advice}"))
    print(f"\n{points} of {total} points.")
    return 1 if percent < args.min_score else 0


if __name__ == "__main__":
    sys.exit(main())
