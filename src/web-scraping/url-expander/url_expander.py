"""Follow redirects to see where a short link really goes, and strip tracking junk from URLs."""
import argparse
import sys
import urllib.error  # web-ok: the network is only used when you don't pass --no-follow
import urllib.request
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

USER_AGENT = "daily-automation-scripts/1.0 (url expander)"
TRACKING = {"fbclid", "gclid", "msclkid", "mc_cid", "mc_eid", "igshid", "ref_src", "_hsenc",
            "_hsmi", "yclid", "dclid", "twclid"}


def clean_url(url):
    """Lowercase scheme and host and drop tracking query parameters (utm_*, fbclid, ...)."""
    parts = urlsplit(url.strip())
    keep = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if not k.lower().startswith("utm_") and k.lower() not in TRACKING]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, urlencode(keep),
                       parts.fragment))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def next_hop(url, timeout=10):
    """Ask the server about `url` without following. Returns (status, Location or '')."""
    opener = urllib.request.build_opener(NoRedirect)
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
        try:
            with opener.open(request, timeout=timeout) as response:
                return response.status, ""
        except urllib.error.HTTPError as err:
            if method == "HEAD" and err.code in (403, 405, 501):
                continue
            return err.code, err.headers.get("Location", "") or ""
    return 0, ""


def follow(url, max_hops=10, timeout=10):
    """Return (chain, outcome). chain is a list of (url, status); outcome says how it ended."""
    chain = []
    for _ in range(max_hops + 1):
        status, location = next_hop(url, timeout)
        chain.append((url, status))
        if 300 <= status < 400 and location:
            nxt = urljoin(url, location)
            if any(nxt == seen for seen, _ in chain):
                return chain, "redirect loop"
            url = nxt
        else:
            return chain, "ok" if status < 400 else f"ended with HTTP {status}"
    return chain, f"stopped after {max_hops} redirects"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Expand short links and clean tracking junk.")
    parser.add_argument("urls", nargs="+", help="URLs to expand")
    parser.add_argument("--no-follow", action="store_true",
                        help="don't contact the server; only clean the URL")
    parser.add_argument("--clean", action="store_true", help="remove tracking parameters")
    parser.add_argument("--chain", action="store_true", help="show every redirect hop")
    parser.add_argument("--max-hops", type=int, default=10, help="most redirects to follow (10)")
    args = parser.parse_args(argv)

    status = 0
    for url in args.urls:
        if not url.lower().startswith(("http://", "https://")):
            print(f"SKIP  not an http(s) URL: {url}")
            status = 1
            continue
        if args.no_follow:
            print(f"{url}\n  -> {clean_url(url) if args.clean else url}")
            continue
        try:
            chain, outcome = follow(url, args.max_hops)
        except (urllib.error.URLError, OSError, ValueError) as err:
            print(f"ERROR {url}  ({getattr(err, 'reason', err)})")
            status = 1
            continue
        final = clean_url(chain[-1][0]) if args.clean else chain[-1][0]
        print(f"{url}\n  -> {final}  [{outcome}, {len(chain) - 1} redirect(s)]")
        if args.chain:
            for hop, code in chain:
                print(f"     {code}  {hop}")
        status = status or (0 if outcome == "ok" else 1)
    return status


if __name__ == "__main__":
    sys.exit(main())
