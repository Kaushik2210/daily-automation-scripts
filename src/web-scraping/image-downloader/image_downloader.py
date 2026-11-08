"""List the images on a page and download them to a folder. Dry run by default."""
import argparse
import mimetypes
import re
import sys
import urllib.error  # web-ok: the network is only used when you give a URL or use --apply
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

USER_AGENT = "daily-automation-scripts/1.0 (image downloader)"
MAX_PAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_BYTES = 20 * 1024 * 1024
LAZY_ATTRS = ("data-src", "data-lazy-src", "data-original")


def best_from_srcset(srcset):
    """Pick the largest candidate (by w or x descriptor) from a srcset attribute."""
    best, best_size = "", -1.0
    for candidate in srcset.split(","):
        parts = candidate.split()
        if not parts:
            continue
        match = re.fullmatch(r"([\d.]+)[wx]", parts[1]) if len(parts) > 1 else None
        size = float(match.group(1)) if match else 0.0
        if size > best_size:
            best, best_size = parts[0], size
    return best


class ImageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = {k: (v or "").strip() for k, v in attrs}
        if tag == "meta" and attrs.get("property") == "og:image":
            self.urls.append(attrs.get("content", ""))
        elif tag in ("img", "source"):
            srcset = attrs.get("srcset") or attrs.get("data-srcset")
            if srcset:
                self.urls.append(best_from_srcset(srcset))
            elif tag == "img":
                self.urls.append(next((attrs[a] for a in LAZY_ATTRS if attrs.get(a)),
                                      attrs.get("src", "")))


def find_images(html, base="", extensions=None):
    """Return unique absolute image URLs in page order."""
    parser = ImageParser()
    parser.feed(html)
    found, seen = [], set()
    for raw in parser.urls:
        if not raw or raw.startswith(("data:", "blob:", "javascript:")):
            continue
        url = urljoin(base, raw)
        if urlsplit(url).scheme not in ("http", "https") and base:
            continue
        ext = Path(unquote(urlsplit(url).path)).suffix.lower().lstrip(".")
        if extensions and ext not in extensions:
            continue
        if url not in seen:
            seen.add(url)
            found.append(url)
    return found


def file_name(url, content_type=""):
    name = re.sub(r"[^\w.\- ]+", "_", Path(unquote(urlsplit(url).path)).name).strip(" .") or "image"
    if not Path(name).suffix:
        name += mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".img"
    return name


def free_path(folder, name):
    """Return a path in folder that doesn't exist yet (adds -2, -3... if needed)."""
    target, count = folder / name, 1
    while target.exists():
        count += 1
        target = folder / f"{Path(name).stem}-{count}{Path(name).suffix}"
    return target


def download(url, folder):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        kind = response.headers.get("Content-Type", "")
        if kind and not kind.startswith(("image/", "application/octet-stream")):
            raise ValueError(f"not an image ({kind.split(';')[0]})")
        data = response.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("larger than 20 MB")
    target = free_path(folder, file_name(url, kind))
    target.write_bytes(data)
    return target, len(data)


def fetch_page(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(MAX_PAGE_BYTES).decode(charset, errors="replace")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Download all the images from a page.")
    parser.add_argument("source", help="a page URL, or a saved .html file")
    parser.add_argument("--base", default="", help="page address, to resolve links in a saved file")
    parser.add_argument("--out", type=Path, default=Path("images"), help="download folder (images)")
    parser.add_argument("--ext", action="append", metavar="EXT",
                        help="only these types, e.g. --ext jpg --ext png")
    parser.add_argument("--limit", type=int, default=100, help="most images to take (100)")
    parser.add_argument("--apply", action="store_true", help="actually download the images")
    args = parser.parse_args(argv)

    path, base = Path(args.source), args.base
    try:
        if "://" in args.source:
            html, base = fetch_page(args.source), base or args.source
        elif path.is_file():
            html = path.read_text(encoding="utf-8", errors="replace")
        else:
            parser.error(f"not a URL or a file: {args.source}")
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't load {args.source}: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    extensions = {e.lower().lstrip(".") for e in args.ext} if args.ext else None
    urls = find_images(html, base, extensions)[:max(args.limit, 0)]
    if not urls:
        print("No images found.")
        return 1
    if not base and any(not urlsplit(u).netloc for u in urls):
        print("Some images use relative addresses; add --base https://site.example/ to resolve.")
    failed = 0
    for number, url in enumerate(urls, 1):
        if not args.apply:
            print(f"{number}. would download {url}")
            continue
        try:
            args.out.mkdir(parents=True, exist_ok=True)
            target, size = download(url, args.out)
            print(f"{number}. saved {target} ({size:,} bytes)")
        except (urllib.error.URLError, OSError, ValueError) as err:
            failed += 1
            print(f"{number}. failed {url}: {getattr(err, 'reason', err)}")
    if not args.apply:
        print(f"{len(urls)} image(s) found. Dry run - add --apply to download them to {args.out}.")
    else:
        print(f"Downloaded {len(urls) - failed} of {len(urls)} image(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
