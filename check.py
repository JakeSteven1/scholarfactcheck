#!/usr/bin/env python3
"""
check.py — fast pre-push checks for scholarfactcheck.com (stdlib only).

    python3 check.py                 # run all checks; exit 1 on any failure
    python3 check.py --write-sitemap # rewrite sitemap.xml from the pages on disk, then check

Checks every *.html outside _archive/ and .git/:
  1. tags are balanced / closed
  2. every internal href / src resolves to a real file or folder
  3. exactly one <h1>, a <title>, a meta description, canonical URL == folder
  4. Tailwind is loaded and the shared header + footer are present
  5. sitemap.xml lists every real page and nothing else
Redirect stubs (<meta http-equiv="refresh">) are exempt from 3–5.
"""

import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
SITE_URL = "https://scholarfactcheck.com"
IGNORE_DIRS = {"_archive", ".git", "__pycache__", "node_modules"}

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}

NAV_LINKS = {"/", "/ben-shapiro-bio-and-positions/", "/jordan-peterson-bio-positions/",
             "/sam-harris-bio/", "/noam-chomsky-bio-positions/", "/christopher-hitchens-bio-and-positions/"}
FOOTER_LINKS = NAV_LINKS - {"/"} | {"/recent-posts/", "/submission-guidelines/", "/errors/",
                                    "/contact-us/", "/privacy-policy-3/", "/privacy-policy-2/"}


class Page(HTMLParser):
    """Collects everything the checks need in one pass."""

    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.stack = []
        self.tag_errors = []
        self.links = []          # (attr, value, line)
        self.h1 = 0
        self.title = None
        self.description = None
        self.canonical = None
        self.redirect = False
        self.noindex = False
        self.tailwind = False
        self.has_header = self.has_footer = False
        self.ids = {}
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        if tag not in VOID:
            self.stack.append((tag, line))
        if tag == "h1":
            self.h1 += 1
        elif tag == "title":
            self._in_title = True
            self.title = ""
        elif tag == "meta":
            if a.get("name") == "description":
                self.description = (a.get("content") or "").strip()
            if a.get("http-equiv", "").lower() == "refresh":
                self.redirect = True
            if a.get("name") == "robots" and "noindex" in (a.get("content") or ""):
                self.noindex = True
        elif tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        elif tag == "script" and "cdn.tailwindcss.com" in (a.get("src") or ""):
            self.tailwind = True
        elif tag == "header" and "sticky" in (a.get("class") or ""):
            self.has_header = True
        elif tag == "footer":
            self.has_footer = True
        if a.get("id"):
            self.ids.setdefault(a["id"], []).append(line)
        for attr in ("href", "src"):
            if a.get(attr) is not None:
                self.links.append((attr, a[attr], line))

    def handle_startendtag(self, tag, attrs):
        # <br />, <path … />, <svg … />: self-closing, never pushed
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1][0] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in VOID:
            return
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
            return
        names = [t for t, _ in self.stack]
        if tag in names:
            i = len(names) - 1 - names[::-1].index(tag)
            for t, l in self.stack[i + 1:]:
                self.tag_errors.append(f"line {l}: <{t}> never closed (closed by </{tag}> at line {self.getpos()[0]})")
            del self.stack[i:]
        else:
            self.tag_errors.append(f"line {self.getpos()[0]}: stray </{tag}>")

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def finish(self):
        self.close()
        for t, l in self.stack:
            self.tag_errors.append(f"line {l}: <{t}> never closed")


def site_pages():
    for p in sorted(ROOT.rglob("*.html")):
        if not (set(p.relative_to(ROOT).parts[:-1]) & IGNORE_DIRS):
            yield p


def page_url(path):
    rel = path.relative_to(ROOT)
    if rel.name == "index.html":
        folder = rel.parent.as_posix()
        return "/" if folder == "." else f"/{folder}/"
    return "/" + rel.as_posix()


def resolve_internal(url, from_path):
    """Return True if a root-relative or relative URL maps to a file/folder on disk."""
    u = urlsplit(url)
    if u.scheme or u.netloc or url.startswith("//") or url.startswith("#") or not u.path:
        return True  # external, mailto:, data:, fragment-only — not ours to check
    target = ROOT / u.path.lstrip("/") if u.path.startswith("/") else from_path.parent / u.path
    if target.is_file():
        return True
    if target.is_dir():
        return u.path.endswith("/") and (target / "index.html").is_file()
    return False


def check_sitemap(real_pages):
    failures = []
    sm = ROOT / "sitemap.xml"
    if not sm.is_file():
        return ["sitemap.xml: missing"]
    listed = set(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sm.read_text(encoding="utf-8")))
    expected = {SITE_URL + u for u in real_pages}
    for u in sorted(expected - listed):
        failures.append(f"sitemap.xml: missing {u}")
    for u in sorted(listed - expected):
        failures.append(f"sitemap.xml: lists {u}, which is not a real page")
    return failures


def write_sitemap(pages):
    """pages: {url: path}. lastmod from <time datetime> in the page, else today."""
    rows = []
    for url, path in sorted(pages.items()):
        html = path.read_text(encoding="utf-8")
        m = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})"', html)
        lastmod = m.group(1) if m else date.today().isoformat()
        if url == "/":
            rows.append((url, lastmod, "weekly", "1.0"))
        else:
            hub = url.rstrip("/").endswith(("bio-and-positions", "bio-positions", "bio"))
            rows.append((url, lastmod, "monthly", "0.9" if hub else "0.7"))
    rows.sort(key=lambda r: (r[0] != "/", r[0]))
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, lastmod, freq, prio in rows:
        out += ["  <url>", f"    <loc>{SITE_URL}{url}</loc>", f"    <lastmod>{lastmod}</lastmod>",
                f"    <changefreq>{freq}</changefreq>", f"    <priority>{prio}</priority>", "  </url>"]
    out.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote sitemap.xml with {len(rows)} URLs")


def main(argv):
    failures = []
    real_pages = {}   # url -> path, for the sitemap check
    count = 0

    for path in site_pages():
        count += 1
        rel = path.relative_to(ROOT).as_posix()
        page = Page(path)
        try:
            page.feed(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError as e:
            failures.append(f"{rel}: not valid UTF-8 ({e})")
            continue
        page.finish()

        # 1. balanced tags
        failures += [f"{rel}: {e}" for e in page.tag_errors]

        # 2. internal links
        for attr, value, line in page.links:
            if not resolve_internal(value, path):
                failures.append(f"{rel}: line {line}: {attr}=\"{value}\" does not resolve")

        for id_, lines in page.ids.items():
            if len(lines) > 1:
                failures.append(f"{rel}: duplicate id=\"{id_}\" on lines {lines}")

        if page.redirect:
            continue  # redirect stubs are exempt from content/layout/sitemap checks

        # 3. head + h1
        url = page_url(path)
        if page.h1 != 1:
            failures.append(f"{rel}: expected exactly one <h1>, found {page.h1}")
        if not (page.title or "").strip():
            failures.append(f"{rel}: missing <title>")
        if not page.description:
            failures.append(f"{rel}: missing <meta name=\"description\">")
        elif len(page.description) > 170:
            failures.append(f"{rel}: meta description is {len(page.description)} chars (keep it under 160)")
        if page.canonical != SITE_URL + url:
            failures.append(f"{rel}: canonical is {page.canonical!r}, expected {SITE_URL + url!r}")

        # 4. Tailwind + shared chrome
        if not page.tailwind:
            failures.append(f"{rel}: does not load Tailwind (cdn.tailwindcss.com)")
        if not page.has_header:
            failures.append(f"{rel}: shared site <header> not found")
        if not page.has_footer:
            failures.append(f"{rel}: shared <footer> not found")
        hrefs = {v for a, v, _ in page.links if a == "href"}
        for missing in sorted(NAV_LINKS - hrefs):
            failures.append(f"{rel}: nav is missing link to {missing}")
        for missing in sorted(FOOTER_LINKS - hrefs):
            failures.append(f"{rel}: footer is missing link to {missing}")
        for id_ in ("nav-toggle", "nav-menu", "js-date", "js-year"):
            if id_ not in page.ids:
                failures.append(f"{rel}: shared chrome element id=\"{id_}\" not found")

        if not page.noindex:
            real_pages[url] = path

    # 5. sitemap
    if "--write-sitemap" in argv:
        write_sitemap(real_pages)
    failures += check_sitemap(real_pages)

    if failures:
        print(f"✗ {len(failures)} problem(s) across {count} HTML files:\n")
        for f in failures:
            print("  " + f)
        return 1
    print(f"✓ {count} HTML files checked, {len(real_pages)} pages in sitemap.xml — all clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
