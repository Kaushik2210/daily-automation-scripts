"""Publish the built site to the gh-pages branch from your own machine, with no GitHub Actions.

Usage: python web/publish_site.py            (dry run: builds and shows what would change)
       python web/publish_site.py --push     (really updates the gh-pages branch)
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from build_site import build
from dashboard import ROOT

SITE_URL = "https://kaushik2210.github.io/daily-automation-scripts/"


def git(*args, cwd):
    """Run a git command and return its text output; raises CalledProcessError on failure."""
    proc = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          encoding="utf-8")
    return proc.stdout


def branch_exists(remote, branch, cwd="."):
    return bool(git("ls-remote", "--heads", remote, branch, cwd=cwd).strip())


def publish(site, remote, branch="gh-pages", message="site: update the live tool pages",
            push=True):
    """Make `branch` of `remote` hold exactly the files in `site`.

    Returns 'pushed', 'unchanged' or 'dry-run'. The branch is updated with a normal commit and a
    normal push, never a force-push.
    """
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        if branch_exists(remote, branch, tmp):
            git("clone", "--quiet", "--branch", branch, "--single-branch", remote, str(work),
                cwd=tmp)
        else:
            git("clone", "--quiet", remote, str(work), cwd=tmp)
            git("checkout", "--quiet", "--orphan", branch, cwd=work)
        for item in work.iterdir():
            if item.name != ".git":
                shutil.rmtree(item) if item.is_dir() else item.unlink()
        shutil.copytree(site, work, dirs_exist_ok=True)
        git("add", "-A", cwd=work)
        if not git("status", "--porcelain", cwd=work).strip():
            return "unchanged"
        if not push:
            return "dry-run"
        git("commit", "--quiet", "-m", message, cwd=work)
        git("push", "--quiet", "origin", branch, cwd=work)
        return "pushed"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Publish the site to the gh-pages branch.")
    parser.add_argument("--remote", help="git remote URL (default: this repo's origin)")
    parser.add_argument("--branch", default="gh-pages", help="branch to publish to (gh-pages)")
    parser.add_argument("--push", action="store_true",
                        help="really update the branch (default is a dry run)")
    args = parser.parse_args(argv)

    remote = args.remote or git("remote", "get-url", "origin", cwd=ROOT).strip()
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp) / "site"
        tools = build(site, ROOT, repo=remote.removesuffix(".git"))
        print(f"Built {len(tools)} tool page(s).")
        result = publish(site, remote, args.branch, push=args.push)
    messages = {
        "pushed": f"Updated the {args.branch} branch. The site refreshes within a minute or two:\n"
                  f"{SITE_URL}",
        "unchanged": f"Nothing to publish: {args.branch} already matches this build.",
        "dry-run": f"Dry run: {args.branch} would change. Use --push to publish.",
    }
    print(messages[result])
    return 0


if __name__ == "__main__":
    sys.exit(main())
