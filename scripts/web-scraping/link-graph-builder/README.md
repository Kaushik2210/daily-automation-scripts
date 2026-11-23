# link-graph-builder

## Purpose
See the structure of a small website at a glance. The tool follows the links between pages and builds a graph: which pages are linked most, how many clicks each page is from the home page, which pages are **orphans** (nothing links to them, so visitors can't find them), which are **dead ends** (no links out) and which internal links are **broken**. It works on a folder of HTML files (ideal for static sites, with no network at all) or, if you allow it, on a live site. You can export the graph for Graphviz or as JSON.

## Install
Standard library only, Python 3.11+. Nothing to install. (Graphviz is only needed if you want to draw the `.dot` file.)

## Usage
```bash
python link_graph_builder.py --dir site/ [--start index.html] [--dot site.dot] [--json graph.json]
python link_graph_builder.py --url https://example.com/ --fetch [--max-pages 50] [--delay 1]
```
With `--dir`, links are resolved the way a web server would (`blog/` means `blog/index.html`, `../x.html`, `/root-relative.html`, `#anchors` ignored); images and other files count as assets, not pages. With `--url`, only pages on the same site are followed, and **nothing is requested unless you add `--fetch`**; requests are `--delay` seconds apart and capped by `--max-pages`, so only crawl sites you may crawl. `--dot` and `--json` create new files and refuse to overwrite existing ones. The exit code is 1 when broken links or orphan pages are found.

## Example
```bash
python link_graph_builder.py --dir site/ --dot site.dot
```
```
7 page(s), 15 internal link(s), 1 external site(s); start: index.html

Most linked-to pages:
   4 in  index.html  Home
   2 in  about.html  About us
   2 in  blog/index.html  Blog
   2 in  blog/post-1.html  First post
   2 in  blog/post-2.html  Second post

Clicks from the start page:
  0: index.html
    1: about.html
    1: blog/index.html
    1: products.html
      2: blog/post-1.html
      2: blog/post-2.html
      2: team.html

Not reachable by clicking from the start page (orphans):
  secret.html

Broken internal links:
  products.html  ->  old-products.html

External sites linked: github.com
```

## Notes
- Render the graph with `dot -Tpng site.dot -o site.png` after installing Graphviz.
- Links to other sites are listed but never followed.
- Use `broken-link-finder` for a link check of a single page and `sitemap-crawler` to explore a site through its sitemap.
