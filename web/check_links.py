"""Check that every tool has a live page and a downloadable source file.

Usage: python web/check_links.py [--site URL]
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

SITE = "https://kaushik2210.github.io/daily-automation-scripts/"


def fetch(url, timeout=20):
    """Return (status, body text); HTTP errors give their status and an empty body."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as reply:
            return reply.status, reply.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, ""
    except urllib.error.URLError:
        return 0, ""


def check_site(site):
    """Return a list of problems found; an empty list means every link works."""
    site = site.rstrip("/") + "/"
    status, body = fetch(site + "data/tools.json")
    if status != 200:
        return [f"{site}data/tools.json -> {status}"]
    problems = []
    for tool in json.loads(body)["tools"]:
        page = f"{site}tools/{tool['id']}/"
        code, html = fetch(page)
        if code != 200 or f'content="{tool["id"]}"' not in html:
            problems.append(f"{page} -> {code or 'unreachable'}")
        code, _ = fetch(site + tool["source"])
        if code != 200:
            problems.append(f"{site}{tool['source']} -> {code or 'unreachable'}")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check every tool link on the live site.")
    parser.add_argument("--site", default=SITE, help="site URL (default: the GitHub Pages site)")
    args = parser.parse_args(argv)
    problems = check_site(args.site)
    for line in problems:
        print("BROKEN", line)
    print("All tool links work." if not problems else f"{len(problems)} broken link(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
