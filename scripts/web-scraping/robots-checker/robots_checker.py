"""Check whether a URL or path is allowed by a site's robots.txt, for a given crawler name."""
import argparse
import contextlib
import re
import sys
import urllib.error  # web-ok: the network is only used when you don't pass --robots
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

USER_AGENT = "daily-automation-scripts/1.0 (robots checker)"


def parse_robots(text):
    """Return (groups, sitemaps); a group is {'agents': [...], 'rules': [...], 'delay': n}."""
    groups, sitemaps, current, collecting = [], [], None, False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        field = field.lower()
        if field == "user-agent":
            if not collecting:
                current = {"agents": [], "rules": [], "delay": None}
                groups.append(current)
            current["agents"].append(value.lower())
            collecting = True
            continue
        collecting = False
        if field == "sitemap":
            sitemaps.append(value)
        elif current is not None and field in ("allow", "disallow"):
            if value:  # an empty Disallow means "allow everything"
                current["rules"].append((field == "allow", value))
        elif current is not None and field == "crawl-delay":
            with contextlib.suppress(ValueError):
                current["delay"] = float(value)
    return groups, sitemaps


def pick_group(groups, agent):
    """The group for the most specific matching agent name, else the '*' group."""
    agent = agent.lower()
    best, best_len = None, -1
    for group in groups:
        for name in group["agents"]:
            if name != "*" and name in agent and len(name) > best_len:
                best, best_len = group, len(name)
    if best:
        return best
    return next((g for g in groups if "*" in g["agents"]), None)


def pattern_matches(pattern, path):
    regex = re.escape(pattern).replace(r"\*", ".*")
    if regex.endswith(r"\$"):
        regex = regex[:-2] + "$"
    return re.match(regex, path) is not None


def is_allowed(group, path):
    """Longest matching rule wins; on a tie, Allow wins. No matching rule means allowed."""
    if group is None:
        return True, None
    best = None
    for allow, pattern in group["rules"]:
        longer = best is None or len(pattern) > len(best[1])
        tie_allow = best is not None and len(pattern) == len(best[1]) and allow
        if pattern_matches(pattern, path) and (longer or tie_allow):
            best = (allow, pattern)
    return (True, None) if best is None else best


def path_of(target):
    parts = urlsplit(target)
    path = parts.path or "/"
    return path + (f"?{parts.query}" if parts.query else "")


def fetch_robots(target, timeout=15):
    parts = urlsplit(target)
    url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(512 * 1024).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        if err.code in (404, 410):
            return ""  # no robots.txt means everything is allowed
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check URLs against robots.txt.")
    parser.add_argument("targets", nargs="+", help="URLs (or paths when you pass --robots)")
    parser.add_argument("--robots", type=Path, help="a saved robots.txt to check against")
    parser.add_argument("--agent", default="*", help="crawler name to check as (default: *)")
    args = parser.parse_args(argv)
    if args.robots and not args.robots.is_file():
        parser.error(f"not a file: {args.robots}")

    cache, blocked = {}, 0
    for target in args.targets:
        try:
            if args.robots:
                text = args.robots.read_text(encoding="utf-8", errors="replace")
            else:
                if "://" not in target:
                    parser.error("give full URLs, or use --robots with a saved file")
                origin = "{0.scheme}://{0.netloc}".format(urlsplit(target))
                if origin not in cache:
                    cache[origin] = fetch_robots(target)
                text = cache[origin]
        except (urllib.error.URLError, OSError) as err:
            print(f"ERROR   {target}  (couldn't get robots.txt: {getattr(err, 'reason', err)})")
            blocked += 1
            continue
        groups, sitemaps = parse_robots(text)
        group = pick_group(groups, args.agent)
        allowed, rule = is_allowed(group, path_of(target))
        why = f"  (rule: {'Allow' if allowed else 'Disallow'} {rule})" if rule else ""
        print(f"{'ALLOWED' if allowed else 'BLOCKED':<8}{target}{why}")
        blocked += not allowed
        delay = group["delay"] if group else None
        if delay and target == args.targets[-1]:
            print(f"Crawl-delay for {args.agent}: {delay:g} seconds between requests.")
        if sitemaps and target == args.targets[-1]:
            print("Sitemaps: " + ", ".join(sitemaps))
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
