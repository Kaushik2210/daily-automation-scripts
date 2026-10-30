"""Build the static site: one page per tool, running the real script in the browser.

Usage: python web/build_site.py --out _site
"""
import argparse
import ast
import json
import re
import shutil
import sys
from pathlib import Path

from dashboard import ROOT, STATIC, discover, get_schema, readme_sections

REPO = "https://github.com/Kaushik2210/daily-automation-scripts"
NEEDS_NETWORK = {
    "socket", "smtplib", "imaplib", "poplib", "ftplib", "ssl", "telnetlib", "webbrowser",
    "urllib.request", "http.client", "http.server", "xmlrpc.client",
}
NEEDS_SYSTEM = {"subprocess", "multiprocessing", "tkinter", "curses", "winreg", "msvcrt", "ctypes"}
# import name -> package that Pyodide can load
PYODIDE_PACKAGES = {"PIL": "pillow", "yaml": "pyyaml", "numpy": "numpy", "pandas": "pandas",
                    "openpyxl": "openpyxl", "lxml": "lxml", "bs4": "beautifulsoup4"}
PLAN_ITEM = re.compile(r"^- \[[ x]\] (\d\d)\. (\S+) - (.+) \(([a-z-]+)\)$")


def imported_modules(source):
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def browser_support(source):
    """Say whether a script can run inside Pyodide, and why not if it can't."""
    modules = imported_modules(source)
    packages = set()
    for name in sorted(modules):
        top = name.split(".")[0]
        if name in NEEDS_NETWORK or top in NEEDS_NETWORK:
            return {"ok": False, "reason": "it needs network access", "packages": []}
        if top in NEEDS_SYSTEM:
            reason = "it needs to run programs on your computer"
            return {"ok": False, "reason": reason, "packages": []}
        if top in sys.stdlib_module_names:
            continue
        if top in PYODIDE_PACKAGES:
            packages.add(PYODIDE_PACKAGES[top])
        else:
            return {"ok": False, "reason": f"it needs the {top} package", "packages": []}
    return {"ok": True, "reason": "", "packages": sorted(packages)}


def plan_info(root):
    """Map script name -> (day, number) from PLAN.md."""
    info, day = {}, None
    plan = Path(root) / "PLAN.md"
    if not plan.is_file():
        return info
    for line in plan.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Day "):
            day = line[7:9]
        elif day and (m := PLAN_ITEM.match(line)):
            info[m.group(2)] = (day, m.group(1))
    return info


def render_page(prefix, tool_id=""):
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    for key, value in {"__MODE__": "static", "__ROOT__": prefix, "__TOOL__": tool_id,
                       "__TOKEN__": ""}.items():
        page = page.replace(key, value)
    return page


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build(out, root=ROOT, repo=REPO):
    out, root = Path(out), Path(root)
    if out.exists():
        shutil.rmtree(out)
    for name in ("app.css", "app.js", "fx.js"):
        out_file = out / "static" / name
        out_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(STATIC / name, out_file)

    plan = plan_info(root)
    tools = []
    for tool_id, info in discover(root).items():
        path = info["path"]
        source = path.read_text(encoding="utf-8")
        day, num = plan.get(info["name"], ("", ""))
        rel = f"src/{info['category']}/{info['name']}/{path.name}"
        write(out / rel, source)
        tools.append({
            "id": tool_id, "name": info["name"], "category": info["category"],
            "summary": info["summary"], "day": day, "num": num, "source": rel,
            "browser": browser_support(source),
            "schema": get_schema(path),
            "sections": readme_sections(path.parent),
        })
        write(out / "tools" / tool_id / "index.html", render_page("../../../", tool_id))
    tools.sort(key=lambda t: (t["day"] or "99", t["num"] or "99", t["name"]))

    write(out / "data" / "tools.json", json.dumps({"repo": repo, "tools": tools}))
    write(out / "index.html", render_page("./"))
    write(out / "404.html", render_page("./"))
    write(out / ".nojekyll", "")
    return tools


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the static site into a folder.")
    parser.add_argument("--out", type=Path, default=Path("_site"), help="output folder")
    parser.add_argument("--repo", default=REPO, help="GitHub repository URL for source links")
    args = parser.parse_args(argv)
    tools = build(args.out, repo=args.repo)
    runnable = sum(t["browser"]["ok"] for t in tools)
    print(f"Built {len(tools)} tool page(s), {runnable} run in the browser -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
