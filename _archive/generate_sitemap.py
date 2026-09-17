#!/usr/bin/env python3
"""
ScholarFactCheck — Sitemap Generator
Usage:  python3 generate_sitemap.py   (run after generate.py)
Output: sitemap.xml in repo root

lastmod comes from each page's <time datetime="…"> (the WordPress publish
date), not the file's mtime, so regenerating the site doesn't bump every URL.
"""

import re
from pathlib import Path
from datetime import date

BASE_URL = "https://scholarfactcheck.com"

# Published but not worth advertising to search engines
SKIP = {
    'node_modules', 'assets', '_source', '.git',
    'privacy-policy', 'privacy-policy-2', 'privacy-policy-3',
    'errors', 'careers', 'contact-us', 'submission-guidelines',
    'the-scholar-fact-check',   # redirect stub for the old WP front page
}
HUB_SUFFIXES = ('bio-and-positions', 'bio-positions', 'bio')


def generate_sitemap():
    urls = [(f"{BASE_URL}/", date.today().isoformat(), "weekly", "1.0")]

    for path in sorted(Path(".").glob("*/index.html")):
        slug = path.parent.name
        if slug in SKIP or slug.startswith(('_', '.')):
            continue
        html = path.read_text(encoding="utf-8")
        if 'http-equiv="refresh"' in html or 'name="robots" content="noindex"' in html:
            continue
        m = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})"', html)
        lastmod = m.group(1) if m else date.today().isoformat()
        priority = "0.9" if slug.endswith(HUB_SUFFIXES) else "0.7"
        urls.append((f"{BASE_URL}/{slug}/", lastmod, "monthly", priority))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod, changefreq, priority in urls:
        lines += ['  <url>', f'    <loc>{loc}</loc>', f'    <lastmod>{lastmod}</lastmod>',
                  f'    <changefreq>{changefreq}</changefreq>', f'    <priority>{priority}</priority>', '  </url>']
    lines.append('</urlset>')
    Path("sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✓ sitemap.xml generated with {len(urls)} URLs")


if __name__ == "__main__":
    generate_sitemap()
